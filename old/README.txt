WWA Wall Display Package v6

Deploy files to:
  /var/www/atlas_html/wwa

Included files:
  - index.html
  - ingest_warning.py
  - alerts.json
  - ingest_meta.json

Expected workflow:
  1. Your LDM-side process writes the newest warning product to:
       /var/www/atlas_html/wwa/latest_warn.txt
  2. Run:
       /usr/bin/python3 /var/www/atlas_html/wwa/ingest_warning.py
  3. Open:
       http://atlas.niu.edu/wwa/

Current behavior:
  - Only NEW warnings are displayed.
  - Warnings without VTEC are ignored.
  - Only Tornado Warning and Severe Thunderstorm Warning products are considered.
  - Display uses UTC ingest time only.
  - Persistent side panel shows the last 5 warnings from alerts.json.
  - Main display shows:
      * TOR/SVR + WFO
      * UTC ingest time
      * HAZARD text
      * IMPACT text
  - Queue logic:
      * each warning displays at least 5 seconds
      * each warning displays no more than 15 seconds
      * if a new warning arrives after 5 seconds, it can preempt the current one
      * if no new warning arrives, current warning clears after 15 seconds
  - Hazard-specific tones:
      * TOR has a more urgent multi-note tone
      * SVR has a simpler distinct tone

Color coding:
  - TOR base: red
  - Confirmed TOR or considerable tornado damage threat: fuchsia
  - Tornado emergency or catastrophic tornado damage threat: bright fuchsia with white accent
  - SVR base: gold
  - SVR considerable damage threat: deep orange
  - SVR destructive damage threat: purple

Notes:
  - Browser audio requires one manual click on "Enable Audio" after page load.
  - Full Screen button is included for wall display operation.
  - Exact-text duplicate suppression has been removed. Every injected NEW warning is ingested.

Test command:
  cd /var/www/atlas_html/wwa
  /usr/bin/python3 ingest_warning.py


v8 changes:
  - Removed IMPACT from main banner
  - Removed IMPACT from last-5 list
  - Main banner severity colors now match the same TOR/SVR tag logic used in history cards
  - Fixed stale impactText JavaScript reference that broke the page in v7


v9 changes:
  - Added NWS logo/header to main display
  - Moved warning history from right sidebar to bottom dock
  - Restyled history as compact last-5 cards with small TOR/SVR icons
  - Audio button now toggles enable/disable
