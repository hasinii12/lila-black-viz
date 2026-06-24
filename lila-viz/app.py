"""
LILA BLACK — Player Journey Visualization Tool
Built for the LILA Games Product Engineer Written Test
"""

import streamlit as st
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import os
import io
import base64
from scipy.ndimage import gaussian_filter

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LILA BLACK — Player Journey Viz",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Map Config ────────────────────────────────────────────────────────────────
MAP_CONFIG = {
    "AmbroseValley": {"scale": 900,  "origin_x": -370, "origin_z": -473},
    "GrandRift":     {"scale": 581,  "origin_x": -290, "origin_z": -290},
    "Lockdown":      {"scale": 1000, "origin_x": -500, "origin_z": -500},
}

MAP_IMAGE = {
    "AmbroseValley": "minimaps/AmbroseValley_Minimap.png",
    "GrandRift":     "minimaps/GrandRift_Minimap.png",
    "Lockdown":      "minimaps/Lockdown_Minimap.jpg",
}

EVENT_COLORS = {
    "Position":       "#4FC3F7",   # light blue
    "BotPosition":    "#B0BEC5",   # grey
    "Kill":           "#FF5252",   # red
    "Killed":         "#FF9800",   # orange
    "BotKill":        "#CE93D8",   # purple
    "BotKilled":      "#FFCC02",   # yellow
    "KilledByStorm":  "#69F0AE",   # green
    "Loot":           "#FFD740",   # gold
}

EVENT_SYMBOLS = {
    "Position":       "circle",
    "BotPosition":    "circle",
    "Kill":           "x",
    "Killed":         "star",
    "BotKill":        "diamond",
    "BotKilled":      "triangle-up",
    "KilledByStorm":  "pentagon",
    "Loot":           "square",
}

MINIMAP_SIZE = 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ─── Coordinate helpers ────────────────────────────────────────────────────────

def world_to_pixel(x, z, map_id):
    cfg = MAP_CONFIG[map_id]
    u = (x - cfg["origin_x"]) / cfg["scale"]
    v = (z - cfg["origin_z"]) / cfg["scale"]
    px = u * MINIMAP_SIZE
    py = (1 - v) * MINIMAP_SIZE
    return px, py


def add_pixel_cols(df):
    coords = [world_to_pixel(row.x, row.z, row.map_id) for row in df.itertuples()]
    df = df.copy()
    df["px"] = [c[0] for c in coords]
    df["py"] = [c[1] for c in coords]
    return df

# ─── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_all_data(data_dir):
    frames = []
    for day_folder in sorted(os.listdir(data_dir)):
        day_path = os.path.join(data_dir, day_folder)
        if not os.path.isdir(day_path):
            continue
        for fname in os.listdir(day_path):
            fpath = os.path.join(day_path, fname)
            try:
                t = pq.read_table(fpath)
                df = t.to_pandas()
                df["event"] = df["event"].apply(
                    lambda x: x.decode("utf-8") if isinstance(x, bytes) else x
                )
                # parse user/bot from filename
                parts = fname.split("_", 1)
                uid = parts[0] if parts else ""
                df["is_bot"] = not ("-" in uid)   # UUID = human, numeric = bot
                df["day"] = day_folder
                df["filename"] = fname
                frames.append(df)
            except Exception:
                continue
    if not frames:
        return pd.DataFrame()
    full = pd.concat(frames, ignore_index=True)
    # strip .nakama-0 suffix from match_id for display
    full["match_id_clean"] = full["match_id"].str.replace(r"\.nakama-0$", "", regex=True)
    # elapsed seconds from min ts per match
    full["ts_ms"] = full["ts"].astype("int64") // 1_000_000
    min_ts = full.groupby("match_id")["ts_ms"].transform("min")
    full["elapsed_s"] = (full["ts_ms"] - min_ts) / 1000
    return full


def image_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    ext = path.rsplit(".", 1)[-1].lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    b64 = base64.b64encode(data).decode()
    return f"data:{mime};base64,{b64}"

# ─── Plotting helpers ──────────────────────────────────────────────────────────

def make_base_figure(map_id):
    img_path = os.path.join(BASE_DIR, MAP_IMAGE[map_id])
    img_b64 = image_to_base64(img_path)

    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=img_b64,
            xref="x", yref="y",
            x=0, y=0,
            sizex=MINIMAP_SIZE, sizey=MINIMAP_SIZE,
            sizing="stretch",
            layer="below",
        )
    )
    fig.update_xaxes(range=[0, MINIMAP_SIZE], showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(range=[MINIMAP_SIZE, 0], showgrid=False, showticklabels=False, zeroline=False, scaleanchor="x")
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        height=700,
        legend=dict(
            bgcolor="rgba(14,17,23,0.85)",
            bordercolor="#333",
            borderwidth=1,
            font=dict(color="white", size=11),
        ),
    )
    return fig


def plot_journeys(df, map_id, show_paths=True, show_events=True, selected_players=None):
    fig = make_base_figure(map_id)
    df = add_pixel_cols(df)

    if selected_players:
        df = df[df["user_id"].isin(selected_players)]

    players = df["user_id"].unique()
    palette = px.colors.qualitative.Plotly + px.colors.qualitative.Dark24

    # Draw movement paths
    if show_paths:
        pos_events = ["Position", "BotPosition"]
        pos_df = df[df["event"].isin(pos_events)].sort_values(["user_id", "elapsed_s"])
        for i, uid in enumerate(players):
            p = pos_df[pos_df["user_id"] == uid]
            if p.empty:
                continue
            is_bot = p["is_bot"].iloc[0]
            color = palette[i % len(palette)] if not is_bot else "rgba(180,180,180,0.3)"
            label = f"{'BOT' if is_bot else 'Human'}: {uid[:8]}…"
            fig.add_trace(go.Scatter(
                x=p["px"], y=p["py"],
                mode="lines",
                line=dict(color=color, width=1.5 if not is_bot else 0.8,
                          dash="dot" if is_bot else "solid"),
                name=label,
                legendgroup=uid,
                showlegend=True,
                opacity=0.6 if is_bot else 0.85,
                hovertemplate=f"<b>{label}</b><br>Time: %{{customdata:.1f}}s<extra></extra>",
                customdata=p["elapsed_s"],
            ))

    # Draw discrete events
    if show_events:
        discrete = df[~df["event"].isin(["Position", "BotPosition"])]
        for evt, grp in discrete.groupby("event"):
            color = EVENT_COLORS.get(evt, "#FFFFFF")
            symbol = EVENT_SYMBOLS.get(evt, "circle")
            fig.add_trace(go.Scatter(
                x=grp["px"], y=grp["py"],
                mode="markers",
                marker=dict(
                    color=color,
                    symbol=symbol,
                    size=10,
                    line=dict(color="white", width=1),
                ),
                name=f"⬡ {evt}",
                legendgroup=f"evt_{evt}",
                hovertemplate=(
                    f"<b>{evt}</b><br>"
                    "User: %{customdata[0]}<br>"
                    "Time: %{customdata[1]:.1f}s<extra></extra>"
                ),
                customdata=list(zip(grp["user_id"].str[:8], grp["elapsed_s"])),
            ))
    return fig


def plot_heatmap(df, map_id, heatmap_type="kills"):
    fig = make_base_figure(map_id)

    type_map = {
        "kills":       ["Kill", "BotKill"],
        "deaths":      ["Killed", "BotKilled", "KilledByStorm"],
        "storm_deaths":["KilledByStorm"],
        "traffic":     ["Position", "BotPosition"],
        "loot":        ["Loot"],
    }
    events = type_map.get(heatmap_type, ["Kill"])
    sub = df[df["event"].isin(events)].copy()

    if sub.empty:
        st.warning(f"No events of type '{heatmap_type}' found.")
        return fig

    sub = add_pixel_cols(sub)

    # Build density grid
    grid = np.zeros((MINIMAP_SIZE, MINIMAP_SIZE), dtype=float)
    xs = sub["px"].clip(0, MINIMAP_SIZE - 1).astype(int)
    ys = sub["py"].clip(0, MINIMAP_SIZE - 1).astype(int)
    for xi, yi in zip(xs, ys):
        grid[yi, xi] += 1

    sigma = 20 if heatmap_type == "traffic" else 14
    grid = gaussian_filter(grid, sigma=sigma)
    grid = grid / grid.max() if grid.max() > 0 else grid

    # Colorscale per type
    cs_map = {
        "kills":        "Reds",
        "deaths":       "Oranges",
        "storm_deaths": "Greens",
        "traffic":      "Blues",
        "loot":         "YlOrBr",
    }
    colorscale = cs_map.get(heatmap_type, "hot")

    # Build transparent heatmap as RGBA image
    cmap_data = _colorscale_to_rgba(grid, colorscale, alpha_scale=0.75)
    fig.add_layout_image(
        dict(
            source=_ndarray_to_b64(cmap_data),
            xref="x", yref="y",
            x=0, y=0,
            sizex=MINIMAP_SIZE, sizey=MINIMAP_SIZE,
            sizing="stretch",
            layer="above",
        )
    )

    fig.update_layout(title=dict(
        text=f"Heatmap — {heatmap_type.replace('_',' ').title()} ({len(sub):,} events)",
        font=dict(color="white", size=14),
    ))
    return fig


def _colorscale_to_rgba(grid, colorscale_name, alpha_scale=0.75):
    """Convert a 2D density grid to RGBA image using a matplotlib colormap."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cmap = plt.get_cmap(colorscale_name)
    rgba = cmap(grid)           # H x W x 4
    # zero-density → transparent
    alpha_mask = (grid > 0.01).astype(float)
    rgba[:, :, 3] = alpha_mask * alpha_scale * grid
    rgba = (rgba * 255).astype(np.uint8)
    return rgba


def _ndarray_to_b64(arr):
    img = Image.fromarray(arr, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return f"data:image/png;base64,{b64}"


def plot_timeline(match_df, map_id):
    """Animated playback: scatter of all players at each time slice."""
    match_df = add_pixel_cols(match_df)
    pos = match_df[match_df["event"].isin(["Position", "BotPosition"])].copy()
    pos["elapsed_bin"] = (pos["elapsed_s"] // 5 * 5).astype(int)

    frames = []
    for t_bin in sorted(pos["elapsed_bin"].unique()):
        snap = pos[pos["elapsed_bin"] <= t_bin]
        frame_data = []
        for uid, grp in snap.groupby("user_id"):
            is_bot = grp["is_bot"].iloc[0]
            frame_data.append(go.Scatter(
                x=grp["px"], y=grp["py"],
                mode="markers+lines",
                marker=dict(size=6, color="#B0BEC5" if is_bot else "#4FC3F7"),
                line=dict(width=1, color="#B0BEC5" if is_bot else "#4FC3F7"),
                name=uid[:8],
                opacity=0.7,
            ))
        frames.append(go.Frame(data=frame_data, name=str(t_bin),
                               layout=go.Layout(title_text=f"T+{t_bin}s")))

    fig = make_base_figure(map_id)
    if frames:
        fig.frames = frames
        fig.update_layout(
            updatemenus=[dict(
                type="buttons", showactive=False,
                y=1.05, x=0.1,
                buttons=[
                    dict(label="▶ Play",
                         method="animate",
                         args=[None, dict(frame=dict(duration=300, redraw=True),
                                          fromcurrent=True, mode="immediate")]),
                    dict(label="⏸ Pause",
                         method="animate",
                         args=[[None], dict(frame=dict(duration=0), mode="immediate",
                                             transition=dict(duration=0))]),
                ],
                font=dict(color="white"),
                bgcolor="#1e2430",
            )],
            sliders=[dict(
                active=0, y=0, x=0.05, len=0.9,
                currentvalue=dict(prefix="Elapsed: ", suffix="s",
                                   font=dict(color="white", size=12)),
                steps=[dict(args=[[f.name],
                                   dict(frame=dict(duration=300, redraw=True),
                                        mode="immediate")],
                             method="animate",
                             label=f.name)
                       for f in frames],
                bgcolor="#1e2430",
                font=dict(color="white"),
            )],
        )
        # Show first frame
        if frames[0].data:
            for tr in frames[0].data:
                fig.add_trace(tr)
    return fig

# ─── Sidebar ───────────────────────────────────────────────────────────────────

def sidebar_filters(df):
    st.sidebar.image(os.path.join(BASE_DIR, "minimaps/GrandRift_Minimap.png"), use_container_width=True)
    st.sidebar.markdown("## 🎮 LILA BLACK\n### Player Journey Viz")
    st.sidebar.markdown("---")

    # Map filter
    maps = sorted(df["map_id"].dropna().unique())
    selected_map = st.sidebar.selectbox("🗺️ Map", maps, index=0)

    # Day filter
    days = sorted(df["day"].unique())
    selected_days = st.sidebar.multiselect("📅 Day", days, default=days)

    filtered = df[(df["map_id"] == selected_map) & (df["day"].isin(selected_days))]

    # Match filter
    matches = sorted(filtered["match_id_clean"].unique())
    selected_match = st.sidebar.selectbox(
        "🆔 Match",
        ["— All Matches —"] + list(matches),
        index=0,
    )
    if selected_match != "— All Matches —":
        filtered = filtered[filtered["match_id_clean"] == selected_match]

    st.sidebar.markdown("---")

    # Player filter (only for single match)
    selected_players = None
    if selected_match != "— All Matches —":
        players = sorted(filtered["user_id"].unique())
        human_players = [p for p in players if "-" in p]
        bot_players = [p for p in players if "-" not in p]
        st.sidebar.markdown(f"**Players:** {len(human_players)} humans · {len(bot_players)} bots")
        all_or_pick = st.sidebar.radio("Show players", ["All", "Select specific"], horizontal=True)
        if all_or_pick == "Select specific":
            selected_players = st.sidebar.multiselect(
                "Pick players", players,
                default=human_players[:3] if human_players else players[:3],
                format_func=lambda x: f"{'🤖' if '-' not in x else '👤'} {x[:12]}…"
            )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<small>Event Legend</small>", unsafe_allow_html=True
    )
    for evt, color in EVENT_COLORS.items():
        if evt not in ("Position", "BotPosition"):
            st.sidebar.markdown(
                f"<span style='color:{color};font-size:16px'>■</span> {evt}",
                unsafe_allow_html=True,
            )

    return selected_map, selected_days, selected_match, filtered, selected_players

# ─── Stats cards ───────────────────────────────────────────────────────────────

def stat_cards(df):
    humans = df[~df["is_bot"]]["user_id"].nunique()
    bots   = df[df["is_bot"]]["user_id"].nunique()
    matches = df["match_id"].nunique()
    kills   = df[df["event"].isin(["Kill","BotKill"])].shape[0]
    deaths  = df[df["event"].isin(["Killed","BotKilled","KilledByStorm"])].shape[0]
    loots   = df[df["event"] == "Loot"].shape[0]
    storms  = df[df["event"] == "KilledByStorm"].shape[0]

    cols = st.columns(7)
    metrics = [
        ("👤 Humans",   humans),
        ("🤖 Bots",     bots),
        ("🆔 Matches",  matches),
        ("⚔️ Kills",    kills),
        ("💀 Deaths",   deaths),
        ("📦 Loots",    loots),
        ("🌪️ Storm ☠",  storms),
    ]
    for col, (label, val) in zip(cols, metrics):
        col.metric(label, f"{val:,}")

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── Custom CSS ──
    st.markdown("""
    <style>
    html, body, [class*="css"] { background-color: #0e1117; color: #fafafa; }
    .stTabs [data-baseweb="tab"] { background-color: #1e2430; border-radius: 6px 6px 0 0; color: #aaa; padding: 8px 20px; }
    .stTabs [aria-selected="true"] { background-color: #4FC3F7; color: #0e1117; font-weight: 700; }
    .stMetric { background: #1e2430; border-radius: 8px; padding: 12px; }
    div[data-testid="stSidebar"] { background-color: #13161e; }
    </style>
    """, unsafe_allow_html=True)

    st.title("🎮 LILA BLACK — Player Journey Visualization")

    # ── Check data ──
    if not os.path.isdir(DATA_DIR) or not any(
        os.listdir(os.path.join(DATA_DIR, d))
        for d in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, d))
    ):
        st.error("⚠️ No data found in `data/` directory.")
        st.info(
            "**Setup:** Copy the `February_10/`, `February_11/`, … folders "
            "from `player_data.zip` into the `data/` directory next to `app.py`."
        )
        st.stop()

    # ── Load ──
    with st.spinner("Loading player data…"):
        df = load_all_data(DATA_DIR)

    if df.empty:
        st.error("No valid parquet files found.")
        st.stop()

    # ── Sidebar ──
    selected_map, selected_days, selected_match, filtered, selected_players = sidebar_filters(df)

    # ── Stats ──
    st.markdown("### 📊 Overview")
    stat_cards(filtered)
    st.markdown("---")

    # ── Tabs ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️  Player Journeys",
        "🔥  Heatmaps",
        "▶️  Timeline / Playback",
        "📈  Analytics",
    ])

    # ── Tab 1: Journeys ──
    with tab1:
        c1, c2 = st.columns([3, 1])
        with c2:
            show_paths  = st.checkbox("Show movement paths", value=True)
            show_events = st.checkbox("Show event markers", value=True)
            st.markdown("**Human paths** — solid coloured lines")
            st.markdown("**Bot paths** — grey dotted lines")

        with c1:
            if filtered.empty:
                st.warning("No data for this selection.")
            else:
                sample = filtered
                if selected_match == "— All Matches —":
                    # Sample up to 5 matches to keep render fast
                    sample_matches = filtered["match_id"].unique()[:5]
                    sample = filtered[filtered["match_id"].isin(sample_matches)]
                    st.caption(f"Showing {len(sample_matches)} of {filtered['match_id'].nunique()} matches (select a specific match for full detail)")

                fig = plot_journeys(sample, selected_map,
                                    show_paths=show_paths,
                                    show_events=show_events,
                                    selected_players=selected_players)
                st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2: Heatmaps ──
    with tab2:
        htype = st.radio(
            "Heatmap Type",
            ["kills", "deaths", "storm_deaths", "traffic", "loot"],
            format_func=lambda x: {
                "kills": "⚔️ Kill Zones",
                "deaths": "💀 Death Zones",
                "storm_deaths": "🌪️ Storm Deaths",
                "traffic": "🚶 Player Traffic",
                "loot": "📦 Loot Hotspots",
            }[x],
            horizontal=True,
        )
        if filtered.empty:
            st.warning("No data for this selection.")
        else:
            fig = plot_heatmap(filtered, selected_map, heatmap_type=htype)
            st.plotly_chart(fig, use_container_width=True)
            counts = filtered[filtered["event"].isin({
                "kills":        ["Kill","BotKill"],
                "deaths":       ["Killed","BotKilled","KilledByStorm"],
                "storm_deaths": ["KilledByStorm"],
                "traffic":      ["Position","BotPosition"],
                "loot":         ["Loot"],
            }[htype])].shape[0]
            st.caption(f"Total events plotted: **{counts:,}**")

    # ── Tab 3: Timeline ──
    with tab3:
        if selected_match == "— All Matches —":
            st.info("👆 Select a **specific match** in the sidebar to enable timeline playback.")
        else:
            match_data = filtered[filtered["match_id_clean"] == selected_match]
            n_humans = match_data[~match_data["is_bot"]]["user_id"].nunique()
            n_bots   = match_data[match_data["is_bot"]]["user_id"].nunique()
            duration = match_data["elapsed_s"].max()
            st.caption(f"Match: `{selected_match[:20]}…`  |  {n_humans} humans · {n_bots} bots  |  Duration: {duration:.0f}s")
            fig = plot_timeline(match_data, selected_map)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("> 💡 Use the **▶ Play** button or drag the slider to scrub through the match.")

    # ── Tab 4: Analytics ──
    with tab4:
        if filtered.empty:
            st.warning("No data for this selection.")
            st.stop()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Event Distribution")
            event_counts = (
                filtered[~filtered["event"].isin(["Position","BotPosition"])]
                ["event"].value_counts().reset_index()
            )
            event_counts.columns = ["event","count"]
            fig_bar = px.bar(
                event_counts, x="event", y="count", color="event",
                color_discrete_map={e: c for e, c in EVENT_COLORS.items()},
                template="plotly_dark",
                title="Combat & Loot Events",
            )
            fig_bar.update_layout(showlegend=False, paper_bgcolor="#1e2430",
                                   plot_bgcolor="#1e2430")
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            st.subheader("Activity Over Time")
            time_df = filtered.copy()
            time_df["minute"] = (time_df["elapsed_s"] // 60).astype(int)
            activity = (
                time_df[time_df["event"].isin(["Kill","Killed","BotKill","BotKilled","KilledByStorm","Loot"])]
                .groupby(["minute","event"])
                .size().reset_index(name="count")
            )
            if not activity.empty:
                fig_line = px.line(
                    activity, x="minute", y="count", color="event",
                    color_discrete_map={e: c for e, c in EVENT_COLORS.items()},
                    template="plotly_dark",
                    title="Events per Minute",
                    labels={"minute":"Match Minute","count":"Events"},
                )
                fig_line.update_layout(paper_bgcolor="#1e2430", plot_bgcolor="#1e2430")
                st.plotly_chart(fig_line, use_container_width=True)

        st.subheader("Human vs Bot Kill Share")
        col3, col4 = st.columns(2)
        with col3:
            hk = filtered[filtered["event"]=="Kill"].shape[0]
            bk = filtered[filtered["event"]=="BotKill"].shape[0]
            fig_pie = px.pie(
                values=[hk, bk],
                names=["Human Kills (PvP)", "Bot Kills (PvE)"],
                color_discrete_sequence=["#FF5252","#CE93D8"],
                template="plotly_dark",
                title="Kill Composition",
            )
            fig_pie.update_layout(paper_bgcolor="#1e2430")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col4:
            st.subheader("Storm Death Risk")
            storm_pct = (
                filtered[filtered["event"]=="KilledByStorm"].shape[0] /
                max(filtered[filtered["event"].isin(["Killed","BotKilled","KilledByStorm"])].shape[0], 1)
            ) * 100
            kill_pct = 100 - storm_pct
            fig_pie2 = px.pie(
                values=[kill_pct, storm_pct],
                names=["Killed by Player/Bot", "Killed by Storm"],
                color_discrete_sequence=["#FF9800","#69F0AE"],
                template="plotly_dark",
                title="Cause of Death Split",
            )
            fig_pie2.update_layout(paper_bgcolor="#1e2430")
            st.plotly_chart(fig_pie2, use_container_width=True)

        st.subheader("Top Players by Activity")
        top = (
            filtered[~filtered["is_bot"]]
            .groupby("user_id")
            .agg(
                events=("event","count"),
                kills=("event", lambda x: (x.isin(["Kill","BotKill"])).sum()),
                deaths=("event", lambda x: (x.isin(["Killed","BotKilled","KilledByStorm"])).sum()),
                loots=("event", lambda x: (x=="Loot").sum()),
                matches=("match_id","nunique"),
            )
            .sort_values("kills", ascending=False)
            .head(20)
            .reset_index()
        )
        top["kd"] = (top["kills"] / top["deaths"].replace(0,1)).round(2)
        top["user_id"] = top["user_id"].str[:16] + "…"
        st.dataframe(
            top.rename(columns={"user_id":"Player","events":"Total Events",
                                  "kills":"Kills","deaths":"Deaths",
                                  "loots":"Loots","matches":"Matches","kd":"K/D"}),
            use_container_width=True, hide_index=True,
        )


if __name__ == "__main__":
    main()
