import contentRules from "./seller-content-rules.json";
import dictionary from "./seller-dictionary.json";
import { createHash } from "node:crypto";

const descriptions: Record<string, string> = dictionary.descriptions;
const phrases: Record<string, string> = dictionary.phrases;
export const sellerDictionaryRevision = createHash("sha256")
  .update(JSON.stringify(dictionary))
  .digest("hex");

export type SellerDescription = {
  text: string;
  translated: boolean;
  dictionary: boolean;
};

export function sellerDescription(raw: string | null | undefined): SellerDescription | null {
  const original = raw?.trim();
  if (!original) return null;

  const normalized = original
    .replace(/[，,]/g, "，")
    .replace(/[。．.]+$/g, "")
    .replace(/\s+/g, "");
  const translation = Object.hasOwn(descriptions, normalized)
    ? descriptions[normalized]
    : undefined;
  if (translation)
    return { text: cleanSellerText(translation), translated: true, dictionary: true };

  // Текст с китайскими иероглифами нельзя считать переведённым.
  if (/[\u3400-\u9fff\uf900-\ufaff]/u.test(original)) {
    const parts = normalized.split(/[，。；;、]+/u).filter(Boolean);
    if (parts.length > 0 && parts.every((part) => Object.hasOwn(phrases, part))) {
      return {
        text: cleanSellerText(parts.map((part) => `${phrases[part]}.`).join(" ")),
        translated: true,
        dictionary: true,
      };
    }
    return { text: cleanSellerText(original), translated: false, dictionary: false };
  }
  return { text: cleanSellerText(original), translated: true, dictionary: false };
}

const publicRules = contentRules.map(({ pattern }) => new RegExp(pattern, "giu"));

export function cleanSellerText(raw: string | null | undefined): string {
  const original = raw?.trim() ?? "";
  const clean = publicRules.reduce((text, rule) => text.replace(rule, " "), original);
  if (clean === original) return original;
  return clean
    .split("\n")
    .map((line) =>
      line
        .replace(/[ \t]+/g, " ")
        .trim()
        .replace(/(?:^|(?<=[.!！。]))[ ,，;；:：.!！。—–-]+(?=\S|$)/gu, "")
        .replace(/[ ,，;；:：—–-]+(?=[.!！。]|$)/gu, ""),
    )
    .filter((line) => /[^\s.,，;；:：!?！？。—–«»"()（）-]/u.test(line))
    .join("\n")
    .trim();
}
