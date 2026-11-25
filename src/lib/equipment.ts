import { equipmentLabels, equipmentSections, equipmentValues } from "./equipment-translations";

export type EquipmentStatus = "standard" | "optional" | "absent" | "unspecified";
export type EquipmentValue = {
  text: string;
  status: EquipmentStatus;
  translationPending: boolean;
};
export type EquipmentItem = {
  label: string;
  sourceLabel: string;
  sourceValue: string;
  values: EquipmentValue[];
  translationPending: boolean;
};
export type EquipmentGroup = { title: string; sourceTitle: string; items: EquipmentItem[] };

export const equipmentStatusLabels: Record<EquipmentStatus, string> = {
  standard: "В стандартной комплектации",
  optional: "Дополнительно — наличие уточняется",
  absent: "Не предусмотрено для комплектации",
  unspecified: "По данным модели",
};

// Registration can belong to another listing sharing the model spec. Never show it here.
const specificationSections = new Set([
  "牌照信息",
  "基本参数",
  "车身",
  "发动机",
  "电动机",
  "电池/充电",
  "变速箱",
  "底盘转向",
  "车轮制动",
]);
const chinese = /[\u3400-\u9fff]/;

export function translateEquipmentValue(raw: string): {
  text: string;
  translationPending: boolean;
} {
  const value = raw.trim();
  const known = Object.hasOwn(equipmentValues, value) ? equipmentValues[value] : undefined;
  if (known) return { text: known, translationPending: false };
  let text = value;
  let match: RegExpMatchArray | null;
  if ((match = value.match(/^支持(.+)$/))) {
    text = `поддержка ${match[1]}`;
  } else if ((match = value.match(/^([≥≤]?\d+(?:[.\-]\d+)?)英寸$/))) {
    text = `${match[1]}″`;
  } else if ((match = value.match(/^([≥≤]?\d+(?:-\d+)?)喇叭$/))) {
    text = `динамиков: ${match[1]}`;
  } else if ((match = value.match(/^(\d+)色$/))) {
    text = `цветов: ${match[1]}`;
  } else if ((match = value.match(/^(\d+)个$/))) {
    text = `${match[1]} шт.`;
  } else if ((match = value.match(/^(\d+(?:\.\d+)?)万$/))) {
    text = `${Number(match[1]) / 100} Мп`;
  } else if ((match = value.match(/^前排(\d+)个\/后排(\d+)个$/))) {
    text = `спереди: ${match[1]}; сзади: ${match[2]}`;
  } else if ((match = value.match(/^(前排|后排)(\d+)个$/))) {
    text = `${match[1] === "前排" ? "спереди" : "сзади"}: ${match[2]}`;
  } else if ((match = value.match(/^(高低调节|腰部支撑)\((\d+)向\)$/))) {
    text = `${match[1] === "高低调节" ? "регулировка по высоте" : "поясничная поддержка"}: ${match[2]} направления`;
  }
  return { text, translationPending: chinese.test(text) };
}

function status(marker: string): EquipmentStatus {
  return marker === "●" ? "standard" : marker === "○" ? "optional" : "absent";
}

function parseValues(raw: string): EquipmentValue[] {
  const positions: Record<string, string> = {
    前: "Спереди",
    后: "Сзади",
    主: "Водитель",
    副: "Передний пассажир",
  };
  return raw
    .split(/\r?\n/)
    .filter((line) => line.trim())
    .flatMap((line): EquipmentValue[] => {
      const value = line.trim();
      const paired = value.match(/^([前后主副])\s*([●○-])\s*\/\s*([前后主副])\s*([●○-])$/);
      if (paired) {
        return [
          { text: positions[paired[1]], status: status(paired[2]), translationPending: false },
          { text: positions[paired[3]], status: status(paired[4]), translationPending: false },
        ];
      }
      if (/^[-—–]$/.test(value)) return [{ text: "", status: "absent", translationPending: false }];
      const marked = value.match(/^([●○])\s*(.*)$/);
      const translated = translateEquipmentValue(marked ? marked[2] : value);
      return [{ ...translated, status: marked ? status(marked[1]) : "unspecified" }];
    });
}

export function modelEquipment(raw: unknown): EquipmentGroup[] {
  let data: unknown = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return [];
    }
  }
  if (!Array.isArray(data)) return [];
  const groups: EquipmentGroup[] = [];
  const seen = new Set<string>();
  for (const section of data) {
    if (!Array.isArray(section) || typeof section[0] !== "string" || !Array.isArray(section[1]))
      continue;
    const [sourceTitle, entries] = section;
    if (specificationSections.has(sourceTitle)) continue;
    const items: EquipmentItem[] = [];
    for (const entry of entries) {
      if (
        !Array.isArray(entry) ||
        typeof entry[0] !== "string" ||
        (typeof entry[1] !== "string" && typeof entry[1] !== "number")
      )
        continue;
      const sourceLabel = entry[0].trim();
      const sourceValue = String(entry[1]).trim();
      if (!sourceLabel || !sourceValue) continue;
      const key = JSON.stringify([sourceLabel, sourceValue]);
      if (seen.has(key)) continue;
      seen.add(key);
      const knownLabel = Object.hasOwn(equipmentLabels, sourceLabel);
      const label = knownLabel ? equipmentLabels[sourceLabel] : sourceLabel;
      const values = parseValues(sourceValue);
      items.push({
        label,
        sourceLabel,
        sourceValue,
        values,
        translationPending: !knownLabel || values.some((v) => v.translationPending),
      });
    }
    if (items.length)
      groups.push({
        title: Object.hasOwn(equipmentSections, sourceTitle)
          ? equipmentSections[sourceTitle]
          : sourceTitle,
        sourceTitle,
        items,
      });
  }
  return groups;
}
