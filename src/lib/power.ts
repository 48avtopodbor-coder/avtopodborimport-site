const HP_PER_KW = 1.35962;
const powerSections = new Set(["基本参数", "发动机", "电动机"]);

export function specPower(raw: unknown): {
  engineHp: number | null;
  motorHp: number | null;
  totalHp: number | null;
} {
  let data: unknown = raw;
  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch {
      data = null;
    }
  }

  const readings = new Map<string, Set<number>>();
  if (Array.isArray(data)) {
    for (const section of data) {
      if (!Array.isArray(section) || !powerSections.has(section[0]) || !Array.isArray(section[1]))
        continue;
      for (const entry of section[1]) {
        if (
          !Array.isArray(entry) ||
          typeof entry[0] !== "string" ||
          (typeof entry[1] !== "number" && typeof entry[1] !== "string")
        )
          continue;
        const text = String(entry[1]).normalize("NFKC").trim();
        if (!/^\d+(?:\.\d+)?$/u.test(text)) continue;
        const value = Number(text);
        if (!Number.isFinite(value) || value <= 0) continue;
        const key = `${section[0]}:${entry[0].normalize("NFKC").replace(/\s+/gu, "")}`;
        const values = readings.get(key) ?? new Set<number>();
        values.add(value);
        readings.set(key, values);
      }
    }
  }

  const hp = (key: string, factor = 1) => {
    const values = readings.get(key);
    if (values?.size !== 1) return null;
    const rounded = Math.round([...values][0] * factor);
    return Number.isFinite(rounded) && rounded > 0 ? rounded : null;
  };

  return {
    engineHp: hp("发动机:最大马力(Ps)") ?? hp("发动机:最大功率(kW)", HP_PER_KW),
    motorHp:
      hp("电动机:电动机总功率(Ps)") ??
      hp("基本参数:电动机(Ps)") ??
      hp("电动机:电动机总功率(kW)", HP_PER_KW),
    totalHp: hp("电动机:系统综合功率(Ps)") ?? hp("电动机:系统综合功率(kW)", HP_PER_KW),
  };
}

export function powerRows(raw: unknown, fuel: string | null, legacyHp?: number | null) {
  const kind = fuel?.trim().toLowerCase();
  if (kind === "электро" || kind === "гибрид erev") {
    const { motorHp } = specPower(raw);
    return [{ label: "Мощность электромоторов", value: motorHp ? `${motorHp} л.с.` : null }];
  }
  if (kind === "гибрид phev" || kind === "гибрид hev") {
    const { engineHp, motorHp, totalHp } = specPower(raw);
    return [
      { label: "Суммарная мощность", value: totalHp ? `${totalHp} л.с.` : null },
      { label: "ДВС", value: engineHp ? `${engineHp} л.с.` : null },
      { label: "Электромотор", value: motorHp ? `${motorHp} л.с.` : null },
    ];
  }
  return [{ label: "Мощность", value: legacyHp ? `${legacyHp} л.с.` : null }];
}
