WWA Wall Display Package v17

Deploy files to:
  /var/www/atlas_html/wwa

Included files:
  - index.html
  - ingest_warning.py
  - radar_updater.py
  - alerts.json
  - ingest_meta.json
  - radar_latest.png
  - README.txt

Recommended workflow:
  1. Keep radar_latest.png fresh with cron or radar_updater.py.
     Example cron every 3 minutes:
       */3 * * * * /usr/bin/curl -s -o /var/www/atlas_html/wwa/radar_latest.tmp https://mesonet.agron.iastate.edu/data/gis/images/4326/USCOMP/n0q_0.png && mv /var/www/atlas_html/wwa/radar_latest.tmp /var/www/atlas_html/wwa/radar_latest.png

  2. Your LDM-side process writes the newest warning product to:
       /var/www/atlas_html/wwa/latest_warn.txt

  3. Run:
       /usr/bin/python3 /var/www/atlas_html/wwa/ingest_warning.py

What changed in v17:
  - ingest_warning.py now creates a small pre-cropped PNG snapshot for each warning instead of copying the full radar image
  - each alert stores radar_crop metadata so the browser can overlay the polygon and centroid marker correctly on that saved snapshot
  - tile clicks now enter a true preview mode:
      * archived warning shows for up to 15 s
      * if a new live warning arrives, preview is interruptible after 5 s
      * if no new live warning arrives, preview returns to idle after 15 s
  - live alert queue remains separate from preview mode, so clicking a tile no longer blocks new warnings incorrectly
  - the page no longer redraws radar continuously; it only draws when the displayed alert changes

Requirements:
  - Pillow is recommended on the server for fast server-side PNG cropping:
      pip3 install pillow

Behavior:
  - Only NEW warnings are displayed.
  - Warnings without VTEC are ignored.
  - Only Tornado Warning and Severe Thunderstorm Warning products are considered.
  - Display uses UTC ingest time only.
  - Main display shows TOR/SVR + WFO, UTC, HAZARD text, and saved cropped radar snapshot with polygon overlay.
  - Right-side tiles show the last 5 warnings.


v18 fixes:
  - live warnings now hard-expire back to idle after 15 s when no newer warning is queued
  - preview mode still lasts up to 15 s but can yield to a new live warning after 5 s
  - strengthened polygon overlay rendering on archived snapshots by coercing crop values numerically and adding clearer polygon stroke + vertex markers


v19 fixes:
  - radar snapshots now have a no-Pillow fallback: if server-side cropping is unavailable, ingest_warning.py copies the full local radar image for that warning and the browser crops it client-side
  - each alert now records snapshot_cropped true/false so the page knows whether to draw the whole saved snapshot or crop from a copied full-image snapshot
  - this makes radar + polygon display work even if Pillow is not installed


v20 fixes:
  - corrected broken backslash escaping in ingest_warning.py that caused a SyntaxError on startup
  - validated ingest_warning.py syntax before packaging


v21 changes:
  - reverted to the original Pillow-only cropped snapshot approach
  - improved LAT...LON polygon parsing with a looser block fallback
  - ingest_warning.py now prints polygon point count, centroid, and saved radar path
  - removed the full-image fallback path


v24 aesthetic changes on top of stable v21:
  - centered 'Last 5 Warnings' title
  - enlarged the main banner
  - widened the hazard panel
  - enlarged the radar panel to 480x320
  - removed centroid marker from radar image
  - made polygon fill more transparent


v25 aesthetic changes:
  - moved NWS logo and title under the recent warning tiles
  - expanded the main alert banner and radar panel to better fill the blank space
  - added idle.png support for idle mode
  - changed SVR color palette from yellow/orange into a blue spectrum
  - recommended idle.png size matches the on-page radar frame: 620x360 px


v27 fixes:
  - rebuilt from the working v25 package
  - changed only the idle image URL
  - moved the NWS logo/title block to the top of the right column
  - hid the radar label text
  - left radar rendering code untouched


v28 changes:
  - idle mode now shows the SPC activity loop as a real animated <img>, so it animates instead of freezing on one frame
  - removed the 'No active warning' text
  - expanded the alert banner farther toward the warning tiles
  - enlarged and centered the radar/image frame to 700x400


v29 layout changes:
  - removed live-warning explanatory text
  - moved 'Waiting for new warnings.' into the IDLE banner area by using the UTC line under IDLE
  - shifted the banner content closer to the top of the page
  - nudged the audio button upward
  - enlarged the image frame to 760x460 for larger idle/SPC loop and radar snapshots


v30 final layout tweaks:
  - removed preview labeling text and preview tag chip
  - made the hazard text box width match the main banner width
  - reduced top whitespace and overall banner height
  - moved the audio button to the bottom-right


v34 changes from stable v30:
  - removed 'Waiting for new warnings.' from idle mode
  - changed idle banner text to '...scanning...'
  - added a live system-time display inline inside the idle banner
  - warning issued time is shown inline in the banner instead of below
  - radar rendering logic unchanged
