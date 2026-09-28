"""Sorts taming locations into dev/data/Taming/<binding>.dat files.

Steps:
  1. Load the existing dev/data/Taming files.
  2. Merge in WorldSatNav/data/Taming/*.dat (file name = binding).
  3. Merge in ../logbook.dat, binding each name with ../monster.dat
     (e.g. "Tameable Turtle" => "Turtle"). Names with no binding go to unknown.dat.
  4. Save the files that changed.
  5. Copy any dev/data/Taming file that differs into WorldSatNav/data/Taming
     (unknown.dat is kept here, it is not a real binding).

A location is skipped if its binding already has one within ARC_MINUTE_BUFFER
arc minutes. In unknown.dat the names must match as well.
"""

import filecmp
import re
import shutil
from pathlib import Path

import lua_table

DEV_DIR = Path(__file__).resolve().parent
ADDON_DIR = DEV_DIR.parent

LOGBOOK_PATH = ADDON_DIR / "logbook.dat"
MONSTERS_PATH = ADDON_DIR / "monster.dat"
WORLDSATNAV_TAMING_DIR = ADDON_DIR.parent / "WorldSatNav" / "data" / "Taming"
OUTPUT_DIR = DEV_DIR / "data" / "Taming"

UNKNOWN_BINDING = "unknown"
ARC_MINUTE_BUFFER = 8


# ---- Monster bindings -------------------------------------------------------

def load_bindings(path):
    """Reads lines like  "Tameable Turtle" => "Turtle"  into a dict."""
    pattern = re.compile(r'"((?:\\.|[^"\\])*)"\s*=>\s*"((?:\\.|[^"\\])*)"')
    text = path.read_text(encoding="utf-8")
    return {
        lua_table.unescape(name): lua_table.unescape(binding)
        for name, binding in pattern.findall(text)
    }


# ---- Location checks --------------------------------------------------------

def to_arc_minutes(direction, degrees, minutes, negative_direction):
    total = float(degrees or 0) * 60 + float(minutes or 0)
    if direction == negative_direction:
        return -total
    return total


def is_nearby(sextant_a, sextant_b):
    if not sextant_a or not sextant_b:
        return False

    long_a = to_arc_minutes(sextant_a.get("longitude"), sextant_a.get("deg_long"), sextant_a.get("min_long"), "W")
    long_b = to_arc_minutes(sextant_b.get("longitude"), sextant_b.get("deg_long"), sextant_b.get("min_long"), "W")
    lat_a = to_arc_minutes(sextant_a.get("latitude"), sextant_a.get("deg_lat"), sextant_a.get("min_lat"), "S")
    lat_b = to_arc_minutes(sextant_b.get("latitude"), sextant_b.get("deg_lat"), sextant_b.get("min_lat"), "S")

    return abs(long_a - long_b) <= ARC_MINUTE_BUFFER and abs(lat_a - lat_b) <= ARC_MINUTE_BUFFER


# ---- Output files -----------------------------------------------------------

class TamingFiles:
    """The dev/data/Taming files, loaded when first needed and saved if changed."""

    def __init__(self):
        self.entries = {}
        self.added = {}

    def path_for(self, binding):
        file_name = re.sub(r'[<>:"/\\|?*]', "_", binding).strip() or UNKNOWN_BINDING
        return OUTPUT_DIR / f"{file_name}.dat"

    def entries_for(self, binding):
        if binding not in self.entries:
            self.entries[binding] = lua_table.load(self.path_for(binding))
        return self.entries[binding]

    def already_has(self, binding, entry):
        for existing in self.entries_for(binding):
            if binding == UNKNOWN_BINDING and existing.get("name") != entry.get("name"):
                continue
            if is_nearby(existing.get("sextant"), entry.get("sextant")):
                return True
        return False

    def add(self, binding, entry):
        """Adds the entry unless it is already covered. Returns True if added."""
        if not entry.get("sextant") or self.already_has(binding, entry):
            return False
        self.entries_for(binding).append(entry)
        self.added[binding] = self.added.get(binding, 0) + 1
        return True

    def save(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for binding in sorted(self.added):
            path = self.path_for(binding)
            lua_table.save(path, self.entries[binding])
            print(f"  {binding}: +{self.added[binding]} ({len(self.entries[binding])} total) -> {path.name}")
        print(f"Added {sum(self.added.values())} location(s) in total")


# ---- Sources ----------------------------------------------------------------

def merge(files, source_name, entries_with_bindings):
    added = 0
    skipped = 0
    for binding, entry in entries_with_bindings:
        if files.add(binding, entry):
            added += 1
        else:
            skipped += 1
    print(f"{source_name}: added {added}, skipped {skipped}")


def worldsatnav_entries(path):
    binding = path.stem
    for entry in lua_table.load(path):
        if isinstance(entry, dict):
            yield binding, dict(entry)


def logbook_entries(bindings):
    for entry in lua_table.load(LOGBOOK_PATH):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        binding = bindings.get(name, UNKNOWN_BINDING)
        yield binding, {"name": name, "sextant": entry.get("sextant")}


# ---- WorldSatNav sync -------------------------------------------------------

def sync_to_worldsatnav():
    if not WORLDSATNAV_TAMING_DIR.parent.is_dir():
        print(f"WorldSatNav data folder not found, skipping copy: {WORLDSATNAV_TAMING_DIR.parent}")
        return
    WORLDSATNAV_TAMING_DIR.mkdir(exist_ok=True)
    copied = 0
    for path in sorted(OUTPUT_DIR.glob("*.dat")):
        if path.stem == UNKNOWN_BINDING:
            continue
        target = WORLDSATNAV_TAMING_DIR / path.name
        if target.is_file() and filecmp.cmp(path, target, shallow=False):
            continue
        shutil.copy2(path, target)
        copied += 1
        print(f"  copied {path.name} -> WorldSatNav")
    print(f"Copied {copied} file(s) to WorldSatNav")


# ---- Main -------------------------------------------------------------------

def main():
    bindings = load_bindings(MONSTERS_PATH)
    files = TamingFiles()

    if WORLDSATNAV_TAMING_DIR.is_dir():
        for path in sorted(WORLDSATNAV_TAMING_DIR.glob("*.dat")):
            merge(files, f"WorldSatNav {path.name}", worldsatnav_entries(path))

    merge(files, "logbook.dat", logbook_entries(bindings))

    files.save()
    sync_to_worldsatnav()


if __name__ == "__main__":
    main()
