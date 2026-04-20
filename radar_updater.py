#!/usr/bin/env python3
import os
import sys
import time
import urllib.request

WEB_DIR = "/var/www/atlas_html/wwa"
RADAR_SOURCE_URL = "https://mesonet.agron.iastate.edu/data/gis/images/4326/USCOMP/n0q_0.png"
RADAR_LOCAL = os.path.join(WEB_DIR, "radar_latest.png")

def update_once():
    tmp = RADAR_LOCAL + ".tmp"
    try:
        with urllib.request.urlopen(RADAR_SOURCE_URL, timeout=20) as resp:
            data = resp.read()
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, RADAR_LOCAL)
        print("updated {}".format(RADAR_LOCAL))
        return 0
    except Exception as e:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        print("radar update failed: {}".format(e))
        return 1

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--loop":
        try:
            sleep_s = max(5, int(sys.argv[2]))
        except Exception:
            sleep_s = 30
        while True:
            update_once()
            time.sleep(sleep_s)
    else:
        raise SystemExit(update_once())

if __name__ == "__main__":
    main()
