# Analysis: Game Stats Changes (Game 3 vs Game 4 - Latest)

Between game 3 (09:29) and game 4 (13:27), the late-game difficulty scaling feature was implemented. Here's what changed:

## Context

- Files involved: `stats.json` (game telemetry data, 4 sessions recorded)
- Related patterns: Late-game difficulty scaling feature (completed)
- Dependencies: None
- This is an analysis only - no code changes proposed

## Commits Applied Between Games

- Reduce damage upgrade scaling to slow late-game DPS growth
- Add compound HP scaling for enemies after wave 20
- Raise enemy speed cap from 1.6x to 2.0x
- Increase contact damage frequency from every 8 waves to every 5
- Scale MAX_ENEMIES with wave number for late-game pressure

## Overall Results

| Metric | Game 3 (before) | Game 4 (after) | Delta |
|---|---|---|---|
| Waves reached | 51 (quit) | 34 (died) | -17 |
| Survival time | 466.7s | 348.8s | -117.9s |
| Kills | 12,364 | 8,772 | -3,592 |
| Damage dealt | 309,638 | 185,832 | -123,806 |
| Damage taken | 11 | 10 | -1 |
| Level reached | 51 | 46 | -5 |
| XP earned | 127,292 | 65,271 | -62,021 |
| DPS | 663.5 | 532.8 | -130.7 |
| Kills/sec | 26.5 | 25.1 | -1.4 |

## Key Finding: Game now ends by death instead of voluntary quit

- Game 3: Player quit at wave 51 with 14/14 HP (game was too easy, player got bored)
- Game 4: Player died at wave 34 (the difficulty scaling actually created a lethal challenge)

## Wave-by-Wave Comparison

| Wave | G3 Kills | G4 Kills | G3 Enemies | G4 Enemies | G3 Level | G4 Level |
|---|---|---|---|---|---|---|
| 5 | 29 | 33 | 52 | 45 | 5 | 6 |
| 10 | 23 | 142 | 140 | 160 | 9 | 16 |
| 15 | 86 | 455 | 139 | 161 | 14 | 28 |
| 20 | 254 | 402 | 140 | 177 | 22 | 35 |
| 25 | 395 | 313 | 134 | 188 | 30 | 40 |
| 30 | 484 | 240 | 140 | 198 | 39 | 44 |
| 33 | 501 | 200 | 133 | 199 | 43 | 45 |

## Analysis of Changes

1. **Enemy count scaling works**: Enemy count grew from 45 at wave 5 to 199 at wave 33 (game 4), vs staying flat around 133-140 in game 3. The MAX_ENEMIES scaling is clearly active.
2. **Player leveled faster early but hit a wall**: Game 4 player reached level 28 by wave 15 (vs 14 in game 3), but the damage upgrade scaling nerf meant those levels translated to less DPS growth.
3. **Kills per wave peaked then declined**: Game 4 kills peaked around wave 15 (455 kills) then dropped to 200 by wave 33, showing enemies were getting tanky enough (compound HP scaling after wave 20) to outpace player damage.
4. **Weapon stats show uniform reduction**: All four weapons dealt roughly 40-50% less total damage in game 4, consistent with the damage upgrade scaling nerf.
5. **Damage taken remained very low (10 total across entire game)**: The player avoided most contact damage. The death was likely from being overwhelmed rather than accumulated attrition.

## Verdict

The late-game difficulty scaling is working as intended. The game now has an actual endgame that can kill the player instead of going on indefinitely. The wall hits around wave 30-34 where enemy count (199) and compound HP scaling outpace player DPS growth.
