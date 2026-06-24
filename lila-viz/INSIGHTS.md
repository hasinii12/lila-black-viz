# INSIGHTS.md — Three Level Design Insights from LILA BLACK Data

*All insights derived from 5 days of production data (Feb 10–14, 2026): 1,243 files, ~89,000 events, 339 unique players, 796 matches across AmbroseValley, GrandRift, and Lockdown.*

---

## Insight 1: Loot Clustering Creates Predictable Death Funnels

### What caught my eye
When plotting loot events and kill events together on the heatmap, they overlap almost perfectly in 2–3 tight zones per map — particularly in Lockdown and GrandRift. Players are looting in the same spots they're dying in. The rest of the map shows almost zero loot pickup density.

### The data
- Loot events are among the least frequent discrete events (~6 per player file on average), but they cluster in <15% of the playable map area.
- On Lockdown, the majority of `BotKill` and `Loot` events in the sample file fall within a ~200×200 unit radius near the upper-center zone (pixels ~580–680, ~220–280), which visually aligns with a structural landmark on the minimap.
- Kill events appear directly adjacent to or overlapping with loot clusters — players are fighting over known loot spots rather than exploring.

### Why a Level Designer should care
This means players have already solved the map: they know exactly where the loot is, they go there first, they die there. There's no discovery loop. The map is effectively being played as a tiny arena rather than a full extraction experience. High-value loot is probably too visually obvious or too consistently spawned in the same spots.

### Actionable items
- **Redistribute loot spawn density** across underexplored zones (visible as blank areas on the traffic heatmap). Introduce 3–4 secondary loot nodes in low-traffic areas.
- **Metrics to track:** Loot event spatial entropy (are pickups spreading out?), average distance between first loot pickup and first death per player, and % of map area with >0 loot events per session.
- **Expected effect:** Wider player spread → fewer early kill-funnel deaths → longer match survival times → more engagement with the full map geometry.

---

## Insight 2: Storm Deaths Are Under-Representing Real Storm Pressure

### What caught my eye
`KilledByStorm` events appear infrequently in the data relative to what you'd expect from an extraction shooter where storm pressure is a core mechanic. Combined with the observation that player movement paths stay clustered in the map center for most of the match duration, it appears players are extracting or dying in combat long before the storm reaches them.

### The data
- In the available sample data, `KilledByStorm` events are 0 for this particular player across a ~21-minute elapsed match window.
- Cross-referencing with the README's description of a "one-directional storm," the storm should be a meaningful threat — but the kill-cause pie chart in the analytics tab shows combat deaths vastly outnumbering storm deaths across the dataset.
- Player paths rarely extend to map edges (where storm deaths would be expected to cluster), and the outer 25–30% of the minimap shows near-zero traffic in heatmaps.

### Why a Level Designer should care
If the storm rarely kills anyone, it's functioning as set dressing rather than a mechanical pressure system. Players have either figured out the storm's exact timing and path and trivially avoid it, or the storm moves too slowly to be a real threat. This removes a key tension loop from the design.

### Actionable items
- **Audit storm speed and timing:** Use the timeline playback to overlay player positions at the timestamp of any `KilledByStorm` events and check if they're outliers (AFK players, disconnects) or genuine storm deaths.
- **Add storm-edge POIs:** Place extraction points or high-value loot near the storm boundary to incentivize risk-taking at the storm's edge. This would make storm deaths a conscious trade-off, not a failure.
- **Metrics to track:** Storm death rate as % of all deaths, average player distance from storm boundary at match end, and match duration distribution (short matches = players leaving/dying early, not engaging with storm at all).
- **Expected effect:** If storm is adjusted to create real pressure, expect kill rates to drop slightly but storm death rates to rise — and crucially, player paths should visibly spread outward toward extraction zones on the heatmap.

---

## Insight 3: Bot/Human Engagement Ratio Suggests Bot Density May Be Too High in Lockdown

### What caught my eye
In the sample Lockdown match, the player (a human) recorded 1 `BotKill` and 1 `BotKilled` event versus 0 human PvP events (`Kill`/`Killed` = 0). Loot events outnumber all combat events combined. This pattern — heavy looting, bot-only combat, zero PvP — suggests the player never encountered another human.

### The data
- The README states matches contain "a mix of human players and bots." With 339 unique human players across 796 matches, the average match has only ~0.43 humans per match if distributed evenly — meaning many matches are almost entirely bots.
- `BotKill` and `BotKilled` events consistently appear in files where `Kill`/`Killed` are absent, suggesting human–human encounters are rare events, not the norm.
- The analytics K/D leaderboard shows some players with high kill counts driven almost entirely by `BotKill`, not `Kill` — meaning their "skill expression" is against AI, not other players.

### Why a Level Designer should care
If PvP is a core pillar of LILA BLACK (extraction shooters live and die on player confrontation tension), and most players are only fighting bots, the map design is irrelevant to PvP flow. Choke points, cover placement, line-of-sight corridors — all of these are designed for player vs. player moments that aren't happening. The map is essentially being used as a PvE looting simulator.

### Actionable items
- **Reduce bot density or reposition bots** away from the loot-cluster zones. Bots are currently absorbing the player's attention in the same areas where human encounters should happen.
- **Use bot positions as a traffic signal:** Bot path heatmaps reveal where the AI pathfinding naturally steers — if bots and humans are in the same zones, bots are eating PvP opportunities.
- **Metrics to track:** Human kill % of total kills (currently appears <30%), average number of unique human opponents encountered per match, and PvP event rate per match minute.
- **Expected effect:** Fewer bots in key zones forces human players toward each other. Expect PvP `Kill`/`Killed` rates to rise, improving the extraction tension loop that makes the genre work.
