# 🚨 NIU Alerts Monitor

A lightweight, real-time severe weather alert visualization tool built for fast situational awareness.

👉 Live site: https://atlas.niu.edu/alerts/

---

## 🌩️ Overview

**NIU Alerts** is a browser-based monitoring dashboard designed to display and cycle through active severe weather warnings with radar context, audio alerts, and clean visual prioritization.

It’s built for **speed, clarity, and operational use** — whether you're tracking warnings in real time, testing workflows, or just want a slick wall display during active weather.

---

## ⚡ Features

- 🌀 **Real-time warning ingestion**
  - Tornado (TOR), Severe Thunderstorm (SVR), etc.
- 🗺️ **Radar + polygon visualization**
- 🔊 **Custom audio alerts**
- ⏱️ **Dynamic display timing**
- 📜 **Scrollable warning history**
- 📱 **Responsive design**
- 🎯 **Operational UX**

---

## 🧠 Design Philosophy

- **Latency matters** → show warnings immediately  
- **Attention is limited** → highlight the most important info  
- **Context is everything** → pair alerts with radar  
- **Don’t fight the user** → let them scroll, pause, explore  

---

## 🏗️ Tech Stack

- HTML / CSS / JavaScript  
- Canvas rendering  
- Web Audio API / Tone.js  
- NWS warning products + radar feeds  

---

## 🚀 Getting Started

```bash
git clone https://github.com/your-org/niu-alerts.git
cd niu-alerts
python -m http.server 8000
```

Open: http://localhost:8000

---

## 🔧 Configuration

- Alert timing rules  
- Audio profiles  
- Radar sources  
- Styling  

---

## ⚠️ Disclaimer

For research and situational awareness only.  
Always rely on official National Weather Service guidance.

---

## 👨‍🔬 Author

Dr. Vittorio (Victor) Gensini  
Northern Illinois University  
Center for Interdisciplinary Research on Convective Storms (CIRCS)
