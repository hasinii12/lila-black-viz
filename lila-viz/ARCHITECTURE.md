# ARCHITECTURE.md — LILA BLACK Player Journey Viz

## What I Built and Why

**Streamlit + Plotly** — chosen over React/Next.js for two reasons:
1. The primary users are Level Designers, not web engineers. Streamlit's sidebar-filter pattern maps 1:1 onto how a designer thinks: "show me this map, this day, this match."
2. All the heavy work (parquet parsing, coordinate math, heatmap computation) is Python. Keeping it in one language eliminates a data serialization layer.

Plotly handles interactive map overlays (zoom, pan, hover) without any WebGL boilerplate. Scipy's `gaussian_filter` gives smooth density heatmaps in ~5 lines.

---

## Data Flow

```
player_data/
  February_10/ … February_14/
    {user_id}_{match_id}.nakama-0    ← parquet, no extension
         │
         ▼
  pyarrow.read_table()               ← reads raw parquet
  pandas.DataFrame                   ← decode bytes event col
  is_bot flag                        ← inferred from filename UUID vs numeric
  elapsed_s                          ← ts_ms - min(ts_ms) per match_id
         │
         ▼  (cached with @st.cache_data)
  Single merged DataFrame in memory
         │
  ┌──────┼────────────────┐
  ▼      ▼                ▼
Journey  Heatmap       Analytics
Plot     (density       (plotly
(Plotly  grid →         bar/line/pie)
scatter) gaussian →
         RGBA PNG →
         layout_image)
```

All data is loaded once at startup and cached. Sidebar filters slice the cached DataFrame in memory — no repeated I/O.

---

## Coordinate Mapping

The README specifies a 2D UV mapping for each map. Key insight: `y` in the data is **elevation**, not a map coordinate — only `x` and `z` are used for 2D plotting.

```python
MAP_CONFIG = {
    "AmbroseValley": {"scale": 900,  "origin_x": -370, "origin_z": -473},
    "GrandRift":     {"scale": 581,  "origin_x": -290, "origin_z": -290},
    "Lockdown":      {"scale": 1000, "origin_x": -500, "origin_z": -500},
}

def world_to_pixel(x, z, map_id):
    cfg = MAP_CONFIG[map_id]
    u = (x - cfg["origin_x"]) / cfg["scale"]
    v = (z - cfg["origin_z"]) / cfg["scale"]
    px = u * 1024
    py = (1 - v) * 1024    # Y-flip: image origin is top-left
    return px, py
```

The Y-flip (`1 - v`) is critical. Without it, the entire map renders upside down. Validated by spot-checking the sample coordinate from the README (`x=-301.45, z=-355.55` → pixel `(78, 890)` on AmbroseValley).

For the heatmap, pixel coordinates are quantized to integer indices in a 1024×1024 numpy grid, then smoothed with `scipy.ndimage.gaussian_filter` (σ=14 for combat, σ=20 for traffic) and rendered as a transparent RGBA overlay on top of the minimap.

---

## Assumptions Made

| Situation | Assumption |
|---|---|
| `is_bot` detection | Inferred from filename, not from `user_id` column directly (same result, more reliable since the column could be spoofed) |
| `ts` column | Represents elapsed match time in ms since epoch offset, not wall-clock time. Computed `elapsed_s` = `(ts_ms - min_ts_per_match) / 1000` |
| `.nakama-0` suffix | Stripped from `match_id` for display only; the full value is kept for grouping |
| Feb 14 partial day | Included as-is; labeled "February_14" in the day filter with no special treatment |
| "All Matches" journey view | Capped at 5 matches to keep render time under 2s; user warned in the UI |
| Heatmap alpha | Zero-density cells → fully transparent; non-zero scaled by `grid_value × 0.75` to show intensity gradient |

---

## Major Trade-offs

| Decision | What I chose | What I didn't choose | Why |
|---|---|---|---|
| Framework | Streamlit | React + FastAPI | Level Designers aren't waiting for a SPA; Streamlit ships in hours not days |
| Data load | All-in-memory on startup | DuckDB / server-side query | Dataset is ~8MB total; fits in RAM easily, avoids DB setup |
| Heatmap render | Server-side numpy → PNG | Client-side WebGL density | More portable; no GPU requirement; runs fine on free cloud tiers |
| Playback | Plotly frames animation | D3 canvas animation | Plotly gives scrubber + play button for free; D3 would take 10× longer |
| Bot detection | Filename heuristic | ML classifier | The README explicitly documents the UUID vs numeric convention — no model needed |
