// Che168 stores model specifications as [section, [[parameter, value], ...]].
// Use the electric range fields only; total hybrid range and road tests differ.
export function electricRange(raw: unknown, fuel: string | null): string | null {
  if (!fuel || !/^(?:Электро|Электричество|Электрический|纯电动)$/iu.test(fuel.trim())) return null;

  let data: unknown = raw;
  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch {
      return null;
    }
  }
  if (!Array.isArray(data)) return null;

  const ranges = new Map<string, Set<number>>();
  for (const section of data) {
    if (!Array.isArray(section) || !Array.isArray(section[1])) continue;
    for (const entry of section[1]) {
      if (!Array.isArray(entry) || typeof entry[0] !== "string") continue;
      const key = entry[0].normalize("NFKC").replace(/\s+/gu, "");
      const match = /^(NEDC|CLTC|WLTC|WLTP)?纯电续航里程\(km\)$/iu.exec(key);
      if (!match || (typeof entry[1] !== "string" && typeof entry[1] !== "number")) continue;
      const value = String(entry[1]).normalize("NFKC").trim();
      if (!/^\d+(?:\.\d+)?$/u.test(value)) continue;
      const km = Number(value);
      if (!Number.isFinite(km) || km <= 0) continue;
      const cycle = match[1]?.toUpperCase() ?? "цикл не указан";
      const values = ranges.get(cycle) ?? new Set<number>();
      values.add(km);
      ranges.set(cycle, values);
    }
  }
  return (
    [...ranges]
      .filter(([, values]) => values.size === 1)
      .map(([cycle, values]) => `${[...values][0].toLocaleString("ru-RU")} км (${cycle})`)
      .join("; ") || null
  );
}
