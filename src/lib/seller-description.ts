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
  if (translation) return { text: translation, translated: true, dictionary: true };

  // Текст с китайскими иероглифами нельзя считать переведённым.
  if (/[\u3400-\u9fff\uf900-\ufaff]/u.test(original)) {
    const parts = normalized.split(/[，。；;、]+/u).filter(Boolean);
    if (parts.length > 0 && parts.every((part) => Object.hasOwn(phrases, part))) {
      return {
        text: parts.map((part) => `${phrases[part]}.`).join(" "),
        translated: true,
        dictionary: true,
      };
    }
    return { text: original, translated: false, dictionary: false };
  }
  return { text: original, translated: true, dictionary: false };
}
