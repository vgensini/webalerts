#!/home/vgensini/Programs/anaconda3/envs/py37/bin/python
import os
import re
import json
from datetime import datetime, timezone
import time
time.sleep(0.05)

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    import shapefile
except Exception:
    shapefile = None

WEB_DIR = "/var/www/atlas_html/alerts"
LATEST_WARN = os.path.join(WEB_DIR, "latest_warn.txt")
ALERTS_JSON = os.path.join(WEB_DIR, "alerts.json")
META_JSON = os.path.join(WEB_DIR, "ingest_meta.json")
RADAR_LATEST = os.path.join(WEB_DIR, "radar_latest.png")
SNAPSHOT_DIR = os.path.join(WEB_DIR, "radar_snapshots")
MAX_HISTORY = 25
MAX_SNAPSHOTS = 30

RADAR_WORLD = {
    "xSize": 0.005,
    "ySize": -0.005,
    "xOrigin": -126.0,
    "yOrigin": 50.0,
}

MIN_CROP_HEIGHT = 450
CROP_PADDING = 40
SNAPSHOT_WIDTH = 1140
SNAPSHOT_HEIGHT = 690
ASPECT_RATIO = float(SNAPSHOT_WIDTH) / float(SNAPSHOT_HEIGHT)

# -------------------------------------------------------------------
# COUNTY OVERLAY SETTINGS
# -------------------------------------------------------------------
COUNTY_SHP = "/var/www/atlas_html/alerts/shapefiles/cb_2018_us_county_5m.shp"
COUNTY_COLOR = (50, 50, 50, 20)
COUNTY_WIDTH = 1
COUNTY_DRAW_BUFFER = 50

# -------------------------------------------------------------------
# CITY OVERLAY SETTINGS
# -------------------------------------------------------------------
CITY_SHP = "/var/www/atlas_html/alerts/shapefiles/DomesticNames.shp"

CITY_MAX_LABELS = 20
CITY_DOT_RADIUS = 0.05

CITY_DOT_COLOR = (128, 71, 71, 20)
CITY_TEXT_COLOR = (240, 240, 240, 235)
CITY_SHADOW_COLOR = (0, 0, 0, 200)

CITY_LABEL_OFFSET_X = 4
CITY_LABEL_OFFSET_Y = -2
CITY_FONT_SIZE = 12
CITY_EDGE_PAD = 2

# -------------------------------------------------------------------
# STATE OVERLAY SETTINGS
# -------------------------------------------------------------------
STATE_SHP = "/var/www/atlas_html/alerts/shapefiles/cb_2018_us_state_5m.shp"
STATE_COLOR = (6, 176, 0)
STATE_WIDTH = 1
STATE_DRAW_BUFFER = 50

# -------------------------------------------------------------------
# INTERSTATE OVERLAY SETTINGS
# -------------------------------------------------------------------
INTERSTATE_SHP = "/var/www/atlas_html/alerts/shapefiles/us_interstate_highways.shp"
INTERSTATE_COLOR = (8, 2, 176)   # muted blue
INTERSTATE_WIDTH = 1
INTERSTATE_DRAW_BUFFER = 50

# Optional TTF font if you want something specific.
# Leave blank to use PIL default font.
CITY_FONT_PATH = "/usr/share/fonts/ttf/dejavu-sans-bold.ttf"

_county_cache = None
_city_cache = None
_state_cache = None
_interstate_cache = None

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def normalize_space(text):
    return re.sub(r"\s+", " ", (text or "").strip())

def squared_distance(x1, y1, x2, y2):
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy

def load_line_segments(shp_path, cache_name):
    global _county_cache, _state_cache, _interstate_cache

    cache_map = {
        "county": _county_cache,
        "state": _state_cache,
        "interstate": _interstate_cache,
    }

    if cache_map[cache_name] is not None:
        return cache_map[cache_name]

    segments = []

    if shapefile is None:
        print("{} overlay skipped: pyshp/shapefile module not installed".format(cache_name))
        return segments

    if not shp_path or not os.path.exists(shp_path):
        print("{} overlay skipped: shapefile not found: {}".format(cache_name, shp_path))
        return segments

    try:
        sf = shapefile.Reader(shp_path)
        for shp in sf.shapes():
            pts = shp.points
            if not pts:
                continue

            parts = list(shp.parts) + [len(pts)]
            for i in range(len(parts) - 1):
                seg = pts[parts[i]:parts[i + 1]]
                if len(seg) >= 2:
                    segments.append(seg)

        print("{} overlay loaded: {} segments".format(cache_name, len(segments)))
    except Exception as e:
        print("{} load failed: {}".format(cache_name, e))
        segments = []

    if cache_name == "county":
        _county_cache = segments
    elif cache_name == "state":
        _state_cache = segments
    elif cache_name == "interstate":
        _interstate_cache = segments

    return segments

def segment_visible(line, img_w, img_h, draw_buffer):
    for lon, lat in line:
        p = lonlat_to_pixel(lon, lat)
        x = p["x"]
        y = p["y"]
        if (-draw_buffer <= x <= img_w + draw_buffer and
                -draw_buffer <= y <= img_h + draw_buffer):
            return True
    return False

def parse_multiline_field(text, field_name):
    lines = text.splitlines()
    capture = False
    pieces = []
    pattern = re.compile(r"^\s*" + re.escape(field_name) + r"\.\.\.(.*)$", re.IGNORECASE)

    for line in lines:
        if not capture:
            m = pattern.match(line)
            if m:
                first = m.group(1).strip()
                if first:
                    pieces.append(first)
                capture = True
            continue

        stripped = line.rstrip()
        if not stripped.strip():
            break
        if re.match(r"^\s*[A-Z][A-Z0-9 /_-]{1,30}\.\.\.", stripped):
            break
        if re.match(r"^\s*[*]", stripped):
            break
        if re.match(r"^\s*(PRECAUTIONARY/PREPAREDNESS ACTIONS|LAT\.\.\.LON|TIME\.\.\.MOT\.\.\.LOC|SOURCE\.\.\.)", stripped, re.IGNORECASE):
            break

        pieces.append(stripped.strip())

    return normalize_space(" ".join(pieces))


def extract_office_name(text):
    m = re.search(r"^National Weather Service\s+([^\n]+)$", text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""

    office = normalize_space(m.group(1))
    parts = office.rsplit(" ", 1)
    if len(parts) == 2 and len(parts[1]) == 2 and parts[1].isalpha() and "," not in parts[0]:
        office = "{}, {}".format(parts[0], parts[1].upper())
    return office


def parse_polygon(text):
    lines = text.splitlines()
    nums = []
    collecting = False
    stop_re = re.compile(
        r"^(TIME\.\.\.MOT\.\.\.LOC|HAIL\.\.\.|MAX HAIL SIZE|WIND\.\.\.|MAX WIND GUST|"
        r"PRECAUTIONARY/PREPAREDNESS ACTIONS|TORNADO\.\.\.|THUNDERSTORM DAMAGE THREAT\.\.\.|"
        r"SOURCE\.\.\.|IMPACT\.\.\.|HAZARD\.\.\.)",
        re.IGNORECASE
    )

    for line in lines:
        if not collecting:
            m = re.search(r"LAT\.\.\.LON\s*(.*)$", line, re.IGNORECASE)
            if m:
                collecting = True
                nums.extend(re.findall(r"\d{4,6}", m.group(1)))
            continue

        stripped = line.strip()
        if not stripped:
            break
        if stop_re.match(stripped):
            break

        found = re.findall(r"\d{4,6}", line)
        if not found:
            break
        nums.extend(found)

    if len(nums) < 6:
        m = re.search(
            r"LAT\.\.\.LON(.*?)(?:\n\s*\n|TIME\.\.\.MOT\.\.\.LOC|PRECAUTIONARY/PREPAREDNESS ACTIONS|HAZARD\.\.\.|IMPACT\.\.\.|SOURCE\.\.\.)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if m:
            nums = re.findall(r"\d{4,6}", m.group(1))

    if len(nums) < 6:
        return []

    points = []
    for i in range(0, len(nums) - 1, 2):
        lat_token = nums[i]
        lon_token = nums[i + 1]
        try:
            lat = int(lat_token) / 100.0
            lon = -int(lon_token) / 100.0
        except Exception:
            continue
        if 15 <= lat <= 60 and -130 <= lon <= -60:
            points.append([round(lon, 4), round(lat, 4)])

    cleaned = []
    for p in points:
        if not cleaned or cleaned[-1] != p:
            cleaned.append(p)

    if len(cleaned) >= 3 and cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])

    return cleaned


def polygon_centroid(points):
    if not points:
        return None

    pts = points[:]
    if len(pts) >= 3 and pts[0] != pts[-1]:
        pts.append(pts[0])

    if len(pts) < 4:
        base = pts[:-1] if len(pts) > 1 else pts
        lon = sum(p[0] for p in base) / max(1, len(base))
        lat = sum(p[1] for p in base) / max(1, len(base))
        return [round(lon, 4), round(lat, 4)]

    area2 = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross

    if abs(area2) < 1e-9:
        base = pts[:-1]
        lon = sum(p[0] for p in base) / max(1, len(base))
        lat = sum(p[1] for p in base) / max(1, len(base))
        return [round(lon, 4), round(lat, 4)]

    cx /= (3.0 * area2)
    cy /= (3.0 * area2)
    return [round(cx, 4), round(cy, 4)]


def lonlat_to_pixel(lon, lat):
    return {
        "x": (lon - RADAR_WORLD["xOrigin"]) / RADAR_WORLD["xSize"],
        "y": (RADAR_WORLD["yOrigin"] - lat) / abs(RADAR_WORLD["ySize"]),
    }


def compute_crop_bounds(polygon, centroid, img_w, img_h):
    if not centroid:
        return None

    polygon_px = [lonlat_to_pixel(pt[0], pt[1]) for pt in polygon] if polygon else []
    centroid_px = lonlat_to_pixel(centroid[0], centroid[1])

    crop_h = float(MIN_CROP_HEIGHT)
    crop_w = crop_h * ASPECT_RATIO

    if polygon_px:
        xs = [p["x"] for p in polygon_px]
        ys = [p["y"] for p in polygon_px]

        span_x = (max(xs) - min(xs)) + CROP_PADDING * 2
        span_y = (max(ys) - min(ys)) + CROP_PADDING * 2

        crop_h = max(float(MIN_CROP_HEIGHT), span_y)
        crop_w = crop_h * ASPECT_RATIO

        if crop_w < span_x:
            crop_w = span_x
            crop_h = crop_w / ASPECT_RATIO

    sx = int(round(centroid_px["x"] - crop_w / 2.0))
    sy = int(round(centroid_px["y"] - crop_h / 2.0))
    sw = int(round(crop_w))
    sh = int(round(crop_h))

    if sw > img_w:
        sw = img_w
        sx = 0
    if sh > img_h:
        sh = img_h
        sy = 0

    if sx < 0:
        sx = 0
    if sy < 0:
        sy = 0
    if sx + sw > img_w:
        sx = max(0, img_w - sw)
    if sy + sh > img_h:
        sy = max(0, img_h - sh)

    return {"sx": sx, "sy": sy, "sw": sw, "sh": sh}


def make_snapshot_name(alert):
    safe_issued = re.sub(r"[^0-9]", "", alert.get("issued", ""))[:14]
    return "{}_{}_{}_{}.png".format(
        safe_issued or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        alert.get("type", "UNK"),
        alert.get("wfo", "UNK"),
        alert.get("etn", "0000"),
    )


# -------------------------------------------------------------------
# COUNTY OVERLAY
# -------------------------------------------------------------------
def load_county_lines():
    return load_line_segments(COUNTY_SHP, "county")


def segment_might_be_visible(line, img_w, img_h):
    for lon, lat in line:
        p = lonlat_to_pixel(lon, lat)
        x = p["x"]
        y = p["y"]
        if (-COUNTY_DRAW_BUFFER <= x <= img_w + COUNTY_DRAW_BUFFER and
                -COUNTY_DRAW_BUFFER <= y <= img_h + COUNTY_DRAW_BUFFER):
            return True
    return False


def draw_counties(img):
    if ImageDraw is None:
        print("county overlay skipped: Pillow ImageDraw unavailable")
        return img

    county_lines = load_county_lines()
    if not county_lines:
        return img

    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    drawn = 0
    for line in county_lines:
        if not segment_visible(line, img_w, img_h, COUNTY_DRAW_BUFFER):
            continue

        px = []
        for lon, lat in line:
            p = lonlat_to_pixel(lon, lat)
            px.append((p["x"], p["y"]))

        if len(px) >= 2:
            try:
                draw.line(px, fill=COUNTY_COLOR, width=COUNTY_WIDTH)
                drawn += 1
            except Exception:
                pass

    print("county overlay drawn: {} segments".format(drawn))
    return img

def load_state_lines():
    return load_line_segments(STATE_SHP, "state")


def draw_states(img):
    if ImageDraw is None:
        print("state overlay skipped: Pillow ImageDraw unavailable")
        return img

    state_lines = load_state_lines()
    if not state_lines:
        return img

    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    drawn = 0
    for line in state_lines:
        if not segment_visible(line, img_w, img_h, STATE_DRAW_BUFFER):
            continue

        px = []
        for lon, lat in line:
            p = lonlat_to_pixel(lon, lat)
            px.append((p["x"], p["y"]))

        if len(px) >= 2:
            try:
                draw.line(px, fill=STATE_COLOR, width=STATE_WIDTH)
                drawn += 1
            except Exception:
                pass

    print("state overlay drawn: {} segments".format(drawn))
    return img

def load_interstate_lines():
    return load_line_segments(INTERSTATE_SHP, "interstate")


def draw_interstates(img):
    if ImageDraw is None:
        print("interstate overlay skipped: Pillow ImageDraw unavailable")
        return img

    road_lines = load_interstate_lines()
    if not road_lines:
        return img

    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    drawn = 0
    for line in road_lines:
        if not segment_visible(line, img_w, img_h, INTERSTATE_DRAW_BUFFER):
            continue

        px = []
        for lon, lat in line:
            p = lonlat_to_pixel(lon, lat)
            px.append((p["x"], p["y"]))

        if len(px) >= 2:
            try:
                draw.line(px, fill=INTERSTATE_COLOR, width=INTERSTATE_WIDTH)
                drawn += 1
            except Exception:
                pass

    print("interstate overlay drawn: {} segments".format(drawn))
    return img

# -------------------------------------------------------------------
# CITY OVERLAY
# -------------------------------------------------------------------
def get_attr_case_insensitive(rec_dict, keys, default=None):
    for k in keys:
        if k in rec_dict:
            return rec_dict[k]
    lower_map = {}
    for k, v in rec_dict.items():
        lower_map[k.lower()] = v
    for k in keys:
        if k.lower() in lower_map:
            return lower_map[k.lower()]
    return default


def safe_int(val, default=0):
    try:
        if val is None:
            return default
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        s = str(val).replace(",", "").strip()
        if not s:
            return default
        return int(float(s))
    except Exception:
        return default


def load_city_points():
    global _city_cache

    if _city_cache is not None:
        return _city_cache

    _city_cache = []

    if shapefile is None:
        print("city overlay skipped: pyshp/shapefile module not installed")
        return _city_cache

    if not CITY_SHP or not os.path.exists(CITY_SHP):
        print("city overlay skipped: CITY_SHP not found: {}".format(CITY_SHP))
        return _city_cache

    try:
        sf = shapefile.Reader(CITY_SHP, encoding="latin1")
        field_names = [f[0] for f in sf.fields[1:]]

        for sr in sf.iterShapeRecords():
            shp = sr.shape
            rec = sr.record

            # Point, PointZ, PointM, MultiPoint, MultiPointZ, MultiPointM
            if shp.shapeType not in (1, 11, 21, 8, 18, 28):
                continue

            if not shp.points:
                continue

            lon, lat = shp.points[0][0], shp.points[0][1]
            rec_dict = dict(zip(field_names, rec))

            name = get_attr_case_insensitive(
                rec_dict,
                ["feature_na", "feature_name", "name", "name1", "official_na", "official_name", "primary_nam"],
                default=""
            )

            feature_class = get_attr_case_insensitive(
                rec_dict,
                ["feature_cl", "feature_class", "feat_class", "class"],
                default=""
            )

            name = normalize_space(str(name))
            feature_class = normalize_space(str(feature_class))

            if not name:
                continue

            if feature_class and "populated" not in feature_class.lower():
                continue

            _city_cache.append({
                "name": name,
                "lon": lon,
                "lat": lat
            })

        print("city overlay loaded: {} points".format(len(_city_cache)))
    except Exception as e:
        print("city load failed: {}".format(e))
        _city_cache = []

    return _city_cache

def get_city_font():
    if ImageFont is None:
        return None

    if CITY_FONT_PATH:
        try:
            return ImageFont.truetype(CITY_FONT_PATH, CITY_FONT_SIZE)
        except Exception as e:
            print("city font load failed ({}): {}".format(CITY_FONT_PATH, e))

    try:
        return ImageFont.load_default()
    except Exception:
        return None


def boxes_overlap(a, b, pad=2):
    return not (
        a[2] + pad < b[0] or
        a[0] - pad > b[2] or
        a[3] + pad < b[1] or
        a[1] - pad > b[3]
    )


def draw_text_with_shadow(draw, x, y, text, font, fill, shadow_fill):
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw.text((x + dx, y + dy), text, font=font, fill=shadow_fill)
    draw.text((x, y), text, font=font, fill=fill)


def measure_text(draw, text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        try:
            return draw.textsize(text, font=font)
        except Exception:
            return (len(text) * 7, 12)


def draw_cities(region, crop):
    if ImageDraw is None:
        print("city overlay skipped: Pillow ImageDraw unavailable")
        return region

    city_points = load_city_points()
    if not city_points:
        return region

    font = get_city_font()
    draw = ImageDraw.Draw(region, "RGBA")
    region_w, region_h = region.size

    crop_center_x = crop["sx"] + (crop["sw"] / 2.0)
    crop_center_y = crop["sy"] + (crop["sh"] / 2.0)

    visible = []
    for city in city_points:
        full_px = lonlat_to_pixel(city["lon"], city["lat"])
        fx = full_px["x"]
        fy = full_px["y"]

        if fx < crop["sx"] or fx > (crop["sx"] + crop["sw"]):
            continue
        if fy < crop["sy"] or fy > (crop["sy"] + crop["sh"]):
            continue

        # Native-resolution crop: no scaling
        rx = int(round(fx - crop["sx"]))
        ry = int(round(fy - crop["sy"]))

        visible.append({
            "name": city["name"],
            "x": rx,
            "y": ry,
            "dist2": squared_distance(fx, fy, crop_center_x, crop_center_y),
            "name_len": len(city["name"])
        })

    # Prefer nearer places, then shorter names
    visible.sort(key=lambda c: (c["dist2"], c["name_len"], c["name"]))

    # Larger candidate pool than final label count
    visible = visible[:max(CITY_MAX_LABELS * 8, CITY_MAX_LABELS)]

    placed_boxes = []
    drawn = 0

    candidate_offsets = [
        (4, -2),    # right
        (4, -10),   # upper right
        (4, 5),     # lower right
        (-4, -2),   # left
        (-4, -10),  # upper left
        (-4, 5),    # lower left
        (0, -12),   # above
        (0, 7),     # below
    ]

    # Coarse occupancy grid to keep one area from getting overcrowded
    grid_w = 70
    grid_h = 35
    max_per_cell = 2
    cell_counts = {}

    for city in visible:
        x = city["x"]
        y = city["y"]
        name = city["name"]

        cell_key = (x // grid_w, y // grid_h)
        if cell_counts.get(cell_key, 0) >= max_per_cell:
            continue

        dot_box = (
            x - CITY_DOT_RADIUS - 1,
            y - CITY_DOT_RADIUS - 1,
            x + CITY_DOT_RADIUS + 1,
            y + CITY_DOT_RADIUS + 1
        )

        tw, th = measure_text(draw, name, font)

        placed = False
        for ox, oy in candidate_offsets:
            if ox > 0:
                tx = x + ox
            elif ox < 0:
                tx = x + ox - tw
            else:
                tx = x - (tw // 2)

            ty = y + oy
            text_box = (tx, ty, tx + tw, ty + th)

            if (
                text_box[0] < CITY_EDGE_PAD or
                text_box[1] < CITY_EDGE_PAD or
                text_box[2] >= region_w - CITY_EDGE_PAD or
                text_box[3] >= region_h - CITY_EDGE_PAD
            ):
                continue

            collision = False
            for pb in placed_boxes:
                if boxes_overlap(text_box, pb, pad=0) or boxes_overlap(dot_box, pb, pad=0):
                    collision = True
                    break
            if collision:
                continue

            draw.ellipse(dot_box, fill=CITY_DOT_COLOR)
            draw_text_with_shadow(draw, tx, ty, name, font, CITY_TEXT_COLOR, CITY_SHADOW_COLOR)

            placed_boxes.append(text_box)
            placed_boxes.append(dot_box)
            cell_counts[cell_key] = cell_counts.get(cell_key, 0) + 1
            drawn += 1
            placed = True
            break

        if drawn >= CITY_MAX_LABELS:
            break

    print("city overlay drawn: {} labels".format(drawn))
    return region


def snapshot_radar(alert):
    if not os.path.exists(RADAR_LATEST) or os.path.getsize(RADAR_LATEST) == 0:
        print("radar snapshot skipped: radar_latest.png missing or empty")
        return "", None
    if Image is None:
        print("radar snapshot skipped: Pillow is not installed")
        return "", None

    try:
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        with Image.open(RADAR_LATEST) as img:
            img = img.convert("RGBA")
            img = draw_counties(img)
            img = draw_states(img)
            img = draw_interstates(img)

            crop = compute_crop_bounds(alert.get("polygon", []), alert.get("centroid"), img.width, img.height)
            if not crop:
                print("radar snapshot skipped: no valid crop bounds")
                return "", None

            region = img.crop((crop["sx"], crop["sy"], crop["sx"] + crop["sw"], crop["sy"] + crop["sh"]))

            # Cities on the cropped/resized image
            region = draw_cities(region, crop)

            region = region.convert("RGB")

            name = make_snapshot_name(alert)
            dest = os.path.join(SNAPSHOT_DIR, name)
            region.save(dest, format="PNG", optimize=True)
            return os.path.relpath(dest, WEB_DIR).replace("\\", "/"), crop
    except Exception as e:
        print("radar snapshot failed: {}".format(e))
        return "", None


def cleanup_snapshots(alerts):
    try:
        keep = set()
        for a in alerts:
            img = a.get("radar_image", "")
            if img:
                keep.add(os.path.normpath(os.path.join(WEB_DIR, img)))
        if not os.path.isdir(SNAPSHOT_DIR):
            return
        files = sorted(
            [os.path.join(SNAPSHOT_DIR, f) for f in os.listdir(SNAPSHOT_DIR) if f.lower().endswith(".png")],
            key=lambda p: os.path.getmtime(p),
            reverse=True
        )
        for p in files[MAX_SNAPSHOTS:]:
            if os.path.normpath(p) not in keep:
                try:
                    os.remove(p)
                except Exception:
                    pass
    except Exception:
        pass


def parse_vtec_utc(vtec_time):
    try:
        dt = datetime.strptime(vtec_time, "%y%m%dT%H%MZ")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def fmt_utc(dt):
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

def parse_alert(text):
    upper = text.upper()

    hazard_type = None
    if "TORNADO WARNING" in upper:
        hazard_type = "TOR"
    elif "SEVERE THUNDERSTORM WARNING" in upper:
        hazard_type = "SVR"
    else:
        return None

    m = re.search(
    r"/O\.(NEW|CON|EXT|EXA|EXB|UPG|CAN|EXP)\.K([A-Z]{3})\.([A-Z]{2})\.W\.([0-9]{4})\.([0-9]{6}T[0-9]{4}Z)-([0-9]{6}T[0-9]{4}Z)/",upper)
    if not m:
        return None

    vtec = {
    "action": m.group(1),
    "office": m.group(2),
    "phen_sig": m.group(3),
    "etn": m.group(4),
    "begin": m.group(5),
    "end": m.group(6),
}
    if vtec["action"] != "NEW":
        return None

    office = m.group(2)
    hazard_text = parse_multiline_field(text, "HAZARD")
    source_text = parse_multiline_field(text, "SOURCE")
    impact_text = parse_multiline_field(text, "IMPACT")
    office_name = extract_office_name(text)

    tornado_tag = ""
    m2 = re.search(r"TORNADO\.\.\.(OBSERVED|RADAR INDICATED)", upper)
    if m2:
        tornado_tag = m2.group(1).title()

    tornado_damage_threat = ""
    m2 = re.search(r"TORNADO DAMAGE THREAT\.\.\.(CONSIDERABLE|CATASTROPHIC)", upper)
    if m2:
        tornado_damage_threat = m2.group(1).title()

    thunderstorm_damage_threat = ""
    m2 = re.search(r"THUNDERSTORM DAMAGE THREAT\.\.\.(CONSIDERABLE|DESTRUCTIVE)", upper)
    if m2:
        thunderstorm_damage_threat = m2.group(1).title()

    emergency = ("TORNADO EMERGENCY" in upper) or (tornado_damage_threat.upper() == "CATASTROPHIC")
    confirmed_tornado = ("CONFIRMED TORNADO" in upper) or (tornado_tag.upper() == "OBSERVED")

    polygon = parse_polygon(text)
    centroid = polygon_centroid(polygon) if polygon else None

    valid_from_dt = parse_vtec_utc(vtec["begin"])
    valid_to_dt = parse_vtec_utc(vtec["end"])

    issued_utc_str = fmt_utc(valid_from_dt) or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    expires_utc_str = fmt_utc(valid_to_dt)

    return {
    "type": hazard_type,
    "wfo": office or "UNK",
    "office": office or "UNK",
    "issued": issued_utc_str,
    "valid_from": issued_utc_str,
    "valid_to": expires_utc_str,
    "vtec_begin": vtec["begin"],
    "vtec_end": vtec["end"],
    "hazard_text": hazard_text,
    "source_text": source_text,
    "impact_text": impact_text,
    "office_name": office_name,
    "etn": vtec["etn"],
    "vtec_action": vtec["action"],
    "source_file": os.path.basename(LATEST_WARN),
    "polygon": polygon,
    "centroid": centroid,
    "tornado_tag": tornado_tag,
    "tornado_damage_threat": tornado_damage_threat,
    "thunderstorm_damage_threat": thunderstorm_damage_threat,
    "emergency": emergency,
    "confirmed_tornado": confirmed_tornado,
    "radar_image": "",
    "radar_crop": None,
    "snapshot_cropped": True
}


def main():
    if not os.path.exists(LATEST_WARN):
        print("latest_warn.txt not found")
        return

    with open(LATEST_WARN, "r", errors="ignore") as f:
        raw = f.read()

    alert = parse_alert(raw)
    meta = load_json(META_JSON, {})
    meta["last_ingest_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    atomic_write_json(META_JSON, meta)

    if not alert:
        print("not a NEW TOR/SVR warning; ignored")
        return

    radar_image, radar_crop = snapshot_radar(alert)
    alert["radar_image"] = radar_image
    alert["radar_crop"] = radar_crop

    alerts = load_json(ALERTS_JSON, [])
    alerts.append(alert)
    alerts = alerts[-MAX_HISTORY:]
    atomic_write_json(ALERTS_JSON, alerts)
    cleanup_snapshots(alerts)

    msg = "ingested {} {} ETN {}".format(alert["type"], alert["wfo"], alert["etn"])
    msg += " polygon_pts={}".format(len(alert.get("polygon", [])))
    msg += " centroid={}".format(alert.get("centroid"))
    msg += " radar={}".format(alert["radar_image"] if alert["radar_image"] else "NONE")
    print(msg)


if __name__ == "__main__":
    main()