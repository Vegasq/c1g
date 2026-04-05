# SBU: Nuclear Option

A top-down survival shooter built with Python and pygame-ce.

You are Colonel Vinnyk of the SBU. A transport plane carrying a nuclear device bound for Moscow has been shot down by Russian air defense over hostile territory. The bomb broke into 10 components now scattered across a combat zone swarming with Russian zomboids. Recover all parts, assemble the bomb, and complete the mission. Slava Ukraini.

## How to Play

### Quick Start

**macOS / Linux:**
```bash
./run.sh
```

**Windows:**
```powershell
.\run.ps1
```

Both scripts create a virtual environment, install dependencies, and launch the game.

### Manual Setup

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install pygame-ce pytmx
python game.py
```

### Controls

| Action | Keyboard | Gamepad |
|---|---|---|
| Move | WASD / Arrow keys | Left stick / D-pad |
| Aim & Shoot | Automatic (nearest enemy) | Automatic |
| Navigate menus | W/S or Up/Down + Enter | D-pad + A button |
| Back / Pause | Escape | B button |
| Zoom in/out | Mouse scroll wheel | - |

## Gameplay

### Objective

Collect **10 bomb components** from extraction zones (green zones) scattered across the map. Each visit advances the wave, grants XP, and recovers a component. Collect all 10 to assemble the device and complete the mission.

### Core Loop

1. **Survive** waves of Russian zomboids that spawn around the screen edges
2. **Level up** by killing enemies and earning XP — choose from 3 upgrade cards each level
3. **Visit extraction zones** to advance waves and collect bomb parts
4. **Upgrade weapons** — unlock shotgun, piercing, and explosive weapons through level-ups

### Enemy Types

| Type | Traits |
|---|---|
| Basic | Standard zomboid, balanced stats |
| Runner | Fast but fragile |
| Brute | Slow, high HP, high XP reward |
| Shielded | Absorbs first hit with a shield |
| Splitter | Splits into 2 mini zomboids on death |
| Elite | Fast, tanky, high XP reward |
| Shooter | Ranged attacks, strafes at distance |

### Difficulty Selector

When starting a new game, choose from 6 difficulty tiers:

| Difficulty | Spawn Rate | Enemy HP | Enemy Speed |
|---|---|---|---|
| Easy | 1x | 1x | 1x |
| Normal | 2x | 1x | 1x |
| Hard | 4x | 1x | 1x |
| X Hard | 8x | 1.5x | 1.15x |
| XX Hard | 16x | 2.5x | 1.3x |
| XXX Hard | 32x | 4x | 1.5x |

### Roguelite Progression

Upgrades earned during runs persist across deaths. Categories include max HP, movement speed, weapon damage, ally spawn rate, and heal amount. Your profile tracks total runs, best wave reached, and accumulated upgrades.

## Project Structure

```
game.py            Main game loop, rendering, all game logic
assets_manager.py  Sprite loading, tile rendering, asset configuration
progression.py     Roguelite profile system, upgrade categories
balance.toml       Tunable game balance parameters
maps/level1.tmx    Tiled map for terrain rendering
assets/            Sprite sheets, tilesets, UI art, music
test_game.py       Test suite
run.sh / run.ps1   One-command launchers (macOS-Linux / Windows)
```

## Configuration

Edit `balance.toml` to tune game balance without changing code. Covers player stats, enemy types, wave timing, spawn rates, weapon properties, health pickups, and difficulty scaling. Delete the file to regenerate defaults.

## Requirements

- Python 3.10+
- pygame-ce
- pytmx
