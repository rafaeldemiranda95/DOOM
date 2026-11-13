#!/usr/bin/env python3
"""Expand Doom E1M1 (Hangar): keep original geometry, attach new wings, rebuild nodes."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import copy
from pathlib import Path

from omg import WAD
from omg.mapedit import Linedef, MapEditor, Sector, Sidedef, Thing

ROOT = Path(__file__).resolve().parents[1]
IWAD = ROOT / "wad" / "doom1.wad"
OUT_WAD = Path(__file__).resolve().parent / "e1m1_expandido.wad"
STATS_JSON = Path(__file__).resolve().parent / "e1m1_stats.json"
AJBSP = Path(__file__).resolve().parent / "tools" / "ajbsp" / "ajbsp.exe"

# Doom editor numbers (shareware-safe)
T_PLAYER1 = 1
T_SHOTGUY = 9
T_IMP = 3001
T_ZOMBIE = 3004
T_DEMON = 3002
T_SPECTRE = 58
T_SHOTGUN = 2001
T_CHAINGUN = 2002
T_CLIP = 2007
T_SHELLS = 2008
T_STIMPACK = 2011
T_MEDIKIT = 2012
T_HEALTH_BONUS = 2014
T_ARMOR_BONUS = 2015
T_GREEN_ARMOR = 2018
T_BARREL = 2035
T_BULBOX = 2048
T_SHELLBOX = 2049
T_ROCKETBOX = 2046
T_LAMP = 2028


def count_things(things: list) -> dict[str, int]:
    names = {
        T_ZOMBIE: "zombie",
        T_SHOTGUY: "shotgunner",
        T_IMP: "imp",
        T_DEMON: "demon",
        T_SPECTRE: "spectre",
        T_SHOTGUN: "shotgun",
        T_CHAINGUN: "chaingun",
        T_CLIP: "clip",
        T_SHELLS: "shells",
        T_STIMPACK: "stimpack",
        T_MEDIKIT: "medikit",
        T_HEALTH_BONUS: "health_bonus",
        T_ARMOR_BONUS: "armor_bonus",
        T_GREEN_ARMOR: "green_armor",
        T_BARREL: "barrel",
        T_BULBOX: "bullet_box",
        T_SHELLBOX: "shell_box",
        T_ROCKETBOX: "rocket_box",
    }
    out: dict[str, int] = {}
    for t in things:
        key = names.get(t.type, f"type_{t.type}")
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def snapshot(m: MapEditor) -> dict:
    return {
        "vertexes": len(m.vertexes),
        "linedefs": len(m.linedefs),
        "sidedefs": len(m.sidedefs),
        "sectors": len(m.sectors),
        "things": len(m.things),
        "thing_counts": count_things(m.things),
        "bbox": {
            "min_x": min(v.x for v in m.vertexes),
            "min_y": min(v.y for v in m.vertexes),
            "max_x": max(v.x for v in m.vertexes),
            "max_y": max(v.y for v in m.vertexes),
        },
    }


def tech_sector(
    z_floor: int = 0,
    z_ceil: int = 128,
    light: int = 160,
    floor: str = "FLOOR4_8",
    ceil: str = "CEIL3_5",
    special: int = 0,
) -> Sector:
    s = Sector()
    s.z_floor = z_floor
    s.z_ceil = z_ceil
    s.tx_floor = floor
    s.tx_ceil = ceil
    s.light = light
    s.type = special
    s.tag = 0
    return s


def nukage_sector(z_floor: int = -16, z_ceil: int = 128, light: int = 144) -> Sector:
    return tech_sector(z_floor, z_ceil, light, floor="NUKAGE1", special=7)


def wall_side(tex: str = "STARTAN2") -> Sidedef:
    sd = Sidedef()
    sd.tx_mid = tex
    sd.tx_up = "-"
    sd.tx_low = "-"
    sd.off_x = 0
    sd.off_y = 0
    return sd


def add_thing(m: MapEditor, x: int, y: int, typ: int, angle: int = 0, flags: int = 7) -> None:
    """flags 7 = easy|medium|hard (all skills)."""
    t = Thing()
    t.x = int(x)
    t.y = int(y)
    t.angle = int(angle)
    t.type = int(typ)
    t.flags = int(flags)
    m.things.append(t)


def fill_grid(m: MapEditor, x0, y0, x1, y1, nx, ny, types, angle=0) -> None:
    """Scatter things on a grid inside a room."""
    xs = [x0 + (x1 - x0) * (i + 1) // (nx + 1) for i in range(nx)]
    ys = [y0 + (y1 - y0) * (j + 1) // (ny + 1) for j in range(ny)]
    k = 0
    for y in ys:
        for x in xs:
            add_thing(m, x, y, types[k % len(types)], angle)
            k += 1


def mark_openings(m: MapEditor, first_new_sector: int) -> None:
    """Make seams between vanilla and annex sectors passable."""
    for ld in m.linedefs:
        if ld.back == Linedef.NONE or not ld.two_sided:
            continue
        fs = m.sidedefs[ld.front].sector
        bs = m.sidedefs[ld.back].sector
        if fs < first_new_sector and bs < first_new_sector:
            continue
        m.sidedefs[ld.front].tx_mid = "-"
        m.sidedefs[ld.back].tx_mid = "-"
        ld.impassable = False
        ld.block_monsters = False
        ld.action = 0


def expand(m: MapEditor) -> None:
    """Roughly 2x vanilla playable area with an obvious northern grand entrance."""
    first_new_sector = len(m.sectors)

    # =====================================================================
    # A) GRAND NORTH COMPLEX — punch the long outdoor wall at y=-2048
    #    Host sec 1: floor=32 ceil=88 → raise ceil for a blatant doorway.
    #    Opening: (1664,-2048)-(2496,-2048) ≈ 832 units wide.
    # =====================================================================
    m.sectors[1].z_ceil = 160
    m.sectors[1].light = max(m.sectors[1].light, 200)
    NZ0, NZ1 = 32, 160

    # Bright entrance (FLAT14) — 832u opening on the outdoor north wall
    entrance = tech_sector(NZ0, NZ1, 255, floor="FLAT14", ceil="FLAT5_4")
    m.draw_sector(
        [(1664, -2048), (2496, -2048), (2496, -1400), (1664, -1400)],
        sector=entrance,
        sidedef=wall_side("BIGDOOR2"),
    )
    # Hub shares entrance north edge (1664..2496 @ y=-1400)
    m.draw_sector(
        [
            (1400, -1400),
            (1664, -1400),
            (2496, -1400),
            (2800, -1400),
            (2800, -400),
            (1400, -400),
        ],
        sector=tech_sector(NZ0, NZ1, 192, floor="FLAT5_4"),
        sidedef=wall_side("STARTAN3"),
    )
    # West barracks (share hub west wall 1400,-1400..-400)
    m.draw_sector(
        [(600, -1400), (1400, -1400), (1400, -400), (600, -400)],
        sector=tech_sector(NZ0, NZ1, 176, floor="FLOOR7_1"),
        sidedef=wall_side("BROWN1"),
    )
    m.draw_sector(
        [(200, -1400), (600, -1400), (600, -400), (200, -400)],
        sector=tech_sector(NZ0, NZ1, 160, floor="FLOOR7_1"),
        sidedef=wall_side("BROWN96"),
    )
    # East hangar (share hub east 2800,-1400..-400)
    m.draw_sector(
        [(2800, -1400), (3600, -1400), (3600, -400), (2800, -400)],
        sector=tech_sector(NZ0, NZ1, 176),
        sidedef=wall_side("STARTAN2"),
    )
    m.draw_sector(
        [(3600, -1400), (4400, -1400), (4400, -400), (3600, -400)],
        sector=tech_sector(NZ0, NZ1, 160),
        sidedef=wall_side("STARTAN1"),
    )
    # Arena north of hub (share hub north 1400..2800 @ y=-400)
    m.draw_sector(
        [(1400, -400), (2800, -400), (2800, 400), (1400, 400)],
        sector=tech_sector(NZ0, NZ1, 208, floor="FLAT14"),
        sidedef=wall_side("TEKWALL1"),
    )
    # Nukage north of arena — share 1400..2800 @ y=400
    m.draw_sector(
        [
            (1200, 400),
            (1400, 400),
            (2800, 400),
            (3000, 400),
            (3000, 1000),
            (1200, 1000),
        ],
        sector=nukage_sector(NZ0 - 24, NZ1, 160),
        sidedef=wall_side("SLADWALL"),
    )
    # Side labs share arena west/east
    m.draw_sector(
        [(600, -400), (1400, -400), (1400, 400), (600, 400)],
        sector=tech_sector(NZ0, NZ1, 192, floor="FLAT5_4"),
        sidedef=wall_side("STONE2"),
    )
    m.draw_sector(
        [(2800, -400), (3600, -400), (3600, 400), (2800, 400)],
        sector=tech_sector(NZ0, NZ1, 192, floor="FLAT5_4"),
        sidedef=wall_side("STONE2"),
    )
    # Trophy room — full width of nukage north wall
    m.draw_sector(
        [(1200, 1000), (3000, 1000), (3000, 1600), (1200, 1600)],
        sector=tech_sector(NZ0, NZ1, 224, floor="FLAT14"),
        sidedef=wall_side("BIGDOOR2"),
    )

    # =====================================================================
    # B) EAST COMPLEX — host sec 62 floor=104 ceil=184
    # =====================================================================
    EZ0, EZ1 = 104, 200
    m.draw_sector(
        [(3680, -3392), (4300, -3392), (4300, -3552), (3680, -3552)],
        sector=tech_sector(EZ0, EZ1, 255, floor="FLAT14"),
        sidedef=wall_side("BIGDOOR2"),
    )
    # Storage shares corridor east wall
    m.draw_sector(
        [
            (4300, -3000),
            (5200, -3000),
            (5200, -4000),
            (4300, -4000),
            (4300, -3552),
            (4300, -3392),
        ],
        sector=tech_sector(EZ0, EZ1, 160),
        sidedef=wall_side("STARTAN2"),
    )
    # Arsenal shares storage north 4300..5200 @ y=-3000
    m.draw_sector(
        [(4300, -2400), (5200, -2400), (5200, -3000), (4300, -3000)],
        sector=tech_sector(EZ0, EZ1, 200, floor="FLAT5_4"),
        sidedef=wall_side("TEKWALL1"),
    )
    # Crate wing shares storage east 5200,-3000..-4000
    m.draw_sector(
        [(5200, -3000), (6000, -3000), (6000, -4000), (5200, -4000)],
        sector=tech_sector(EZ0, EZ1, 144),
        sidedef=wall_side("STARTAN1"),
    )
    # Brown wing shares arsenal east + crate north corner via 5200,-2400..-3000
    m.draw_sector(
        [(5200, -2400), (6000, -2400), (6000, -3000), (5200, -3000)],
        sector=tech_sector(EZ0, EZ1, 176, floor="FLOOR7_1"),
        sidedef=wall_side("BROWN1"),
    )
    # Nukage yard shares arsenal+brown north 4300..6000 @ -2400
    m.draw_sector(
        [
            (4300, -1800),
            (6000, -1800),
            (6000, -2400),
            (5200, -2400),
            (4300, -2400),
            (4300, -1800),
        ],
        sector=nukage_sector(EZ0 - 24, EZ1, 150),
        sidedef=wall_side("SLADWALL"),
    )
    # Far east annex — west edge split to merge crate + brown east walls
    m.draw_sector(
        [
            (6000, -2400),
            (6800, -2400),
            (6800, -4000),
            (6000, -4000),
            (6000, -3000),
        ],
        sector=tech_sector(EZ0, EZ1, 168, floor="FLAT14"),
        sidedef=wall_side("STONE2"),
    )

    # =====================================================================
    # C) SOUTH COMPLEX — host sec 82 floor=-24 ceil=88
    # =====================================================================
    SZ0, SZ1 = -24, 128
    m.draw_sector(
        [(2912, -4864), (3104, -4864), (3104, -5300), (2912, -5300)],
        sector=tech_sector(SZ0, SZ1, 220, floor="FLAT14"),
        sidedef=wall_side("BIGDOOR2"),
    )
    m.draw_sector(
        [
            (2500, -5300),
            (2912, -5300),
            (3104, -5300),
            (3600, -5300),
            (3600, -6200),
            (2500, -6200),
        ],
        sector=tech_sector(SZ0, SZ1, 160, floor="FLOOR7_1"),
        sidedef=wall_side("BROWN1"),
    )
    m.draw_sector(
        [(3600, -5300), (4400, -5300), (4400, -6200), (3600, -6200)],
        sector=tech_sector(SZ0, SZ1, 150, floor="FLOOR7_1"),
        sidedef=wall_side("BROWN96"),
    )
    m.draw_sector(
        [(2500, -6200), (3600, -6200), (3600, -7000), (2500, -7000)],
        sector=nukage_sector(SZ0 - 16, SZ1, 140),
        sidedef=wall_side("SLADWALL"),
    )
    m.draw_sector(
        [(3600, -6200), (4400, -6200), (4400, -7000), (3600, -7000)],
        sector=tech_sector(SZ0, SZ1, 170, floor="FLAT5_4"),
        sidedef=wall_side("STARTAN2"),
    )

    # =====================================================================
    # D) WEST spur from secret-ish outdoor (linedef 127 @ x=-768)
    #    Host sec 28: floor=0 ceil=128 — wall (-768,-3520)-(-768,-2944)
    # =====================================================================
    WZ0, WZ1 = 0, 128
    m.draw_sector(
        [(-768, -3520), (-768, -2944), (-1400, -2944), (-1400, -3520)],
        sector=tech_sector(WZ0, WZ1, 200, floor="FLAT14"),
        sidedef=wall_side("BIGDOOR2"),
    )
    m.draw_sector(
        [(-1400, -3600), (-1400, -2800), (-2200, -2800), (-2200, -3600)],
        sector=tech_sector(WZ0, WZ1, 160, floor="FLOOR7_1"),
        sidedef=wall_side("BROWN1"),
    )
    m.draw_sector(
        [(-2200, -3400), (-2200, -3000), (-2800, -3000), (-2800, -3400)],
        sector=tech_sector(WZ0, WZ1, 176, floor="FLAT5_4"),
        sidedef=wall_side("STONE2"),
    )

    mark_openings(m, first_new_sector)

    # --- Populate new wings only (dense enough to feel like a new map) ---
    # North entrance + hub
    fill_grid(m, 1700, -2000, 2450, -1450, 3, 2, [T_ZOMBIE, T_SHOTGUY, T_IMP], 270)
    add_thing(m, 2080, -1900, T_LAMP)
    add_thing(m, 2080, -1600, T_STIMPACK)
    add_thing(m, 1900, -1700, T_SHELLS)
    add_thing(m, 2300, -1700, T_CLIP)

    fill_grid(m, 1500, -1300, 2700, -500, 4, 3, [T_ZOMBIE, T_IMP, T_SHOTGUY, T_DEMON], 0)
    add_thing(m, 2100, -900, T_MEDIKIT)
    add_thing(m, 2100, -700, T_GREEN_ARMOR)
    add_thing(m, 1800, -1100, T_LAMP)
    add_thing(m, 2400, -1100, T_LAMP)
    add_thing(m, 2100, -500, T_BARREL)
    add_thing(m, 2000, -600, T_BARREL)

    fill_grid(m, 700, -1300, 1300, -500, 3, 3, [T_IMP, T_ZOMBIE, T_SHOTGUY], 90)
    fill_grid(m, 250, -1300, 550, -300, 2, 3, [T_IMP, T_SPECTRE], 90)
    add_thing(m, 400, -800, T_STIMPACK)
    add_thing(m, 400, -500, T_SHELLBOX)

    fill_grid(m, 2900, -1300, 3500, -500, 3, 3, [T_ZOMBIE, T_IMP, T_SHOTGUY], 270)
    fill_grid(m, 3700, -1300, 4300, -300, 3, 3, [T_IMP, T_DEMON, T_SHOTGUY], 270)
    add_thing(m, 4000, -800, T_CHAINGUN)
    add_thing(m, 3200, -900, T_SHOTGUN)
    add_thing(m, 4000, -500, T_BULBOX)

    fill_grid(m, 1500, -300, 2700, 300, 4, 3, [T_IMP, T_SHOTGUY, T_ZOMBIE, T_SPECTRE], 270)
    fill_grid(m, 1300, 450, 2900, 900, 4, 2, [T_IMP, T_DEMON, T_ZOMBIE], 270)
    add_thing(m, 2100, 0, T_MEDIKIT)
    add_thing(m, 2100, 700, T_STIMPACK)
    add_thing(m, 1800, 600, T_BARREL)
    add_thing(m, 2400, 600, T_BARREL)

    fill_grid(m, 700, -300, 1300, 300, 2, 3, [T_IMP, T_SHOTGUY], 90)
    fill_grid(m, 2900, -300, 3500, 300, 2, 3, [T_IMP, T_ZOMBIE], 270)
    add_thing(m, 1000, 0, T_HEALTH_BONUS)
    add_thing(m, 3200, 0, T_ARMOR_BONUS)

    add_thing(m, 2100, 1300, T_GREEN_ARMOR)
    add_thing(m, 2000, 1200, T_ROCKETBOX)
    add_thing(m, 2200, 1200, T_SHELLBOX)
    add_thing(m, 2100, 1400, T_MEDIKIT)
    add_thing(m, 1900, 1300, T_IMP, 270)
    add_thing(m, 2300, 1300, T_SHOTGUY, 270)

    # East complex
    fill_grid(m, 3750, -3520, 4200, -3420, 3, 1, [T_ZOMBIE, T_SHOTGUY], 180)
    add_thing(m, 4000, -3472, T_LAMP)
    fill_grid(m, 4400, -3900, 5100, -3100, 4, 4, [T_ZOMBIE, T_IMP, T_SHOTGUY, T_DEMON], 0)
    fill_grid(m, 4400, -2900, 5100, -2500, 3, 2, [T_IMP, T_SHOTGUY], 270)
    add_thing(m, 4700, -2700, T_SHOTGUN)
    add_thing(m, 4900, -2700, T_CHAINGUN)
    add_thing(m, 4800, -2600, T_GREEN_ARMOR)
    fill_grid(m, 5300, -3900, 5900, -3100, 3, 3, [T_IMP, T_SPECTRE, T_ZOMBIE], 180)
    fill_grid(m, 5300, -2900, 5900, -2500, 3, 2, [T_SHOTGUY, T_IMP], 270)
    fill_grid(m, 4400, -2300, 5900, -1900, 4, 2, [T_IMP, T_DEMON, T_ZOMBIE], 270)
    fill_grid(m, 6100, -3500, 6700, -2900, 3, 2, [T_IMP, T_SHOTGUY, T_ZOMBIE], 180)
    add_thing(m, 6400, -3200, T_MEDIKIT)
    add_thing(m, 6400, -3000, T_SHELLBOX)
    add_thing(m, 5000, -3500, T_BARREL)
    add_thing(m, 5500, -3300, T_BARREL)
    add_thing(m, 5600, -2100, T_STIMPACK)

    # South complex
    fill_grid(m, 2950, -5200, 3080, -4900, 1, 2, [T_ZOMBIE], 90)
    fill_grid(m, 2600, -6100, 3500, -5400, 4, 3, [T_IMP, T_ZOMBIE, T_SHOTGUY, T_DEMON], 0)
    fill_grid(m, 3700, -6100, 4300, -5400, 3, 3, [T_IMP, T_SHOTGUY], 180)
    fill_grid(m, 2600, -6900, 3500, -6300, 3, 2, [T_IMP, T_SPECTRE], 90)
    fill_grid(m, 3700, -6900, 4300, -6300, 3, 2, [T_ZOMBIE, T_SHOTGUY, T_IMP], 180)
    add_thing(m, 3000, -5700, T_MEDIKIT)
    add_thing(m, 4000, -5700, T_STIMPACK)
    add_thing(m, 3000, -6600, T_SHELLBOX)
    add_thing(m, 4000, -6600, T_BULBOX)
    add_thing(m, 3200, -5800, T_BARREL)
    add_thing(m, 3800, -6500, T_BARREL)

    # West spur
    fill_grid(m, -1300, -3400, -900, -3000, 2, 2, [T_ZOMBIE, T_IMP], 0)
    fill_grid(m, -2100, -3500, -1500, -2900, 3, 3, [T_IMP, T_SHOTGUY, T_ZOMBIE], 0)
    fill_grid(m, -2700, -3300, -2300, -3100, 2, 1, [T_SPECTRE, T_DEMON], 0)
    add_thing(m, -1800, -3200, T_STIMPACK)
    add_thing(m, -2500, -3200, T_MEDIKIT)
    add_thing(m, -2000, -3000, T_SHELLS)
    add_thing(m, -1100, -3200, T_LAMP)


def build_nodes(wad_path: Path) -> None:
    if not AJBSP.is_file():
        raise SystemExit(f"AJBSP not found at {AJBSP}. Run download step first.")
    # -n = no GL nodes (vanilla linuxdoom); classic NODES/BLOCKMAP/REJECT only
    cmd = [str(AJBSP), "-n", "-v", str(wad_path)]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> int:
    if not IWAD.is_file():
        print(f"Missing IWAD: {IWAD}", file=sys.stderr)
        return 1

    src = WAD(str(IWAD))
    m = MapEditor(src.maps["E1M1"])
    before = snapshot(m)
    print("BEFORE", json.dumps(before, indent=2))

    expand(m)
    after_geom = snapshot(m)
    print("AFTER_GEOM", json.dumps({k: after_geom[k] for k in ("vertexes", "linedefs", "sectors", "things", "bbox")}, indent=2))

    out = WAD()
    group = m.to_lumps()
    # Drop stale nodes so AJBSP rebuilds cleanly
    for lump in ("SEGS", "SSECTORS", "NODES", "REJECT", "BLOCKMAP"):
        if lump in group:
            del group[lump]
    out.maps["E1M1"] = group
    OUT_WAD.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(str(OUT_WAD))
    build_nodes(OUT_WAD)

    # Re-read for final stats
    final = WAD(str(OUT_WAD))
    mf = MapEditor(final.maps["E1M1"])
    after = snapshot(mf)
    STATS_JSON.write_text(
        json.dumps({"before": before, "after": after}, indent=2),
        encoding="utf-8",
    )
    print("AFTER", json.dumps(after, indent=2))
    print(f"Wrote {OUT_WAD}")
    print(f"Wrote {STATS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
