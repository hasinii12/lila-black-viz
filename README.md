# 🎮 LILA BLACK — Player Journey Visualization Tool

A web-based tool for Level Designers to explore player behavior across all three LILA BLACK maps using 5 days of production telemetry data.

**Live Demo:** `[Your Streamlit Cloud URL here]`

---

## Features

| Feature | Details |
|---|---|
| 🗺️ Player Journeys | Movement paths rendered on minimap; humans = solid color lines, bots = grey dotted |
| 🔥 Heatmaps | Kill zones, death zones, storm deaths, player traffic, loot hotspots |
| ▶️ Timeline Playback | Animated match playback with scrubber slider (per-match) |
| 🔍 Filters | Filter by map, day, match, and specific players |
| 📈 Analytics | Event distributions, activity-over-time charts, K/D leaderboard, kill composition |
| 👤🤖 Human vs Bot | Visually distinct rendering; stats separated across all views |

---

## Tech Stack

- **Frontend + Backend:** [Streamlit](https://streamlit.io/) — Python-native, zero frontend overhead, fast iteration
- **Data:** Apache Parquet via `pyarrow` + `pandas`
- **Visualization:** `plotly` (interactive charts + map overlays), `matplotlib` (heatmap colormap rendering), `scipy` (gaussian density smoothing)
- **Hosting:** Streamlit Community Cloud (free, GitHub-connected, shareable URL)

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/lila-black-viz.git
cd lila-black-viz
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add data
Unzip `player_data.zip` and copy the day folders into `data/`:
```
lila-black-viz/
├── data/
│   ├── February_10/
│   ├── February_11/
│   ├── February_12/
│   ├── February_13/
│   └── February_14/
├── minimaps/
│   ├── AmbroseValley_Minimap.png
│   ├── GrandRift_Minimap.png
│   └── Lockdown_Minimap.jpg
├── app.py
└── requirements.txt
```

### 4. Run locally
```bash
streamlit run app.py
```

### 5. Deploy to Streamlit Cloud
1. Push repo to GitHub (keep `data/` — it's needed, ~8MB total)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as the main file
4. Deploy — done

### Environment Variables
None required for local or Streamlit Cloud deployment.

---

## Data Notes

- All parquet files have **no `.parquet` extension** — they are read correctly by `pyarrow`
- The `event` column is stored as bytes and decoded with `.decode('utf-8')` on load
- `is_bot` is inferred from the filename: UUID = human, numeric ID = bot
- `elapsed_s` is computed per-match by subtracting the minimum `ts` value within each `match_id`
- February 14 is a partial day

---

## File Structure

```
app.py              — Main Streamlit app (all logic in one file for simplicity)
requirements.txt    — Python dependencies
README.md           — This file
ARCHITECTURE.md     — Technical decisions and coordinate mapping
INSIGHTS.md         — Three data-backed insights for Level Designers
minimaps/           — Map images (1024×1024)
data/               — Parquet telemetry files (added by user)
.streamlit/
  config.toml       — Dark theme config
```
