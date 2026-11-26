"""Read explicitly reported electrified power figures from Che168 specifications."""

import json
import math
import re
import unicodedata

HP_PER_KW = 1.35962
MOTOR_FUELS = frozenset(("электро", "гибрид erev"))
SYSTEM_FUELS = frozenset(("гибрид phev", "гибрид hev"))
ELECTRIFIED_FUELS = MOTOR_FUELS | SYSTEM_FUELS
POWER_SECTIONS = {"基本参数", "发动机", "电动机"}


def spec_power(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = None

    readings = {}
    if isinstance(raw, (list, tuple)):
        for section in raw:
            if (not isinstance(section, (list, tuple)) or len(section) < 2
                    or not isinstance(section[0], str) or section[0] not in POWER_SECTIONS
                    or not isinstance(section[1], (list, tuple))):
                continue
            for entry in section[1]:
                if not isinstance(entry, (list, tuple)) or len(entry) < 2 or not isinstance(entry[0], str):
                    continue
                text = unicodedata.normalize("NFKC", str(entry[1])).strip()
                if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text):
                    continue
                value = float(text)
                if not math.isfinite(value) or value <= 0:
                    continue
                key = re.sub(r"\s+", "", unicodedata.normalize("NFKC", entry[0]))
                readings.setdefault((section[0], key), set()).add(value)

    def hp(section, key, factor=1):
        values = readings.get((section, key), ())
        if len(values) != 1:
            return None
        value = next(iter(values)) * factor
        if not math.isfinite(value):
            return None
        return math.floor(value + 0.5) or None

    return {
        "engine_hp": hp("发动机", "最大马力(Ps)") or hp("发动机", "最大功率(kW)", HP_PER_KW),
        "motor_hp": (hp("电动机", "电动机总功率(Ps)") or hp("基本参数", "电动机(Ps)")
                     or hp("电动机", "电动机总功率(kW)", HP_PER_KW)),
        "total_hp": hp("电动机", "系统综合功率(Ps)") or hp("电动机", "系统综合功率(kW)", HP_PER_KW),
    }


def electrified_power_hp(raw, fuel):
    """Use the first known figure displayed by the site for this fuel type."""
    kind = (fuel or "").strip().casefold()
    if kind not in ELECTRIFIED_FUELS:
        return None
    power = spec_power(raw)
    if kind in MOTOR_FUELS:
        return power["motor_hp"]
    return power["total_hp"] or power["engine_hp"] or power["motor_hp"]
