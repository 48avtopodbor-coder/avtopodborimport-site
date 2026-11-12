// Китайские иероглифы: такие значения не показываем, пока у них нет перевода
const CJK = /[　-〿㐀-䶿一-鿿＀-￯]/;

// Значение для показа на сайте: без иероглифов и с заглавной буквы.
// Возвращает null, если показывать нечего.
export function displayValue(value: string | null | undefined): string | null {
  const v = value?.trim();
  if (!v || CJK.test(v)) return null;
  return v.charAt(0).toLocaleUpperCase("ru") + v.slice(1);
}

// Первое значение, которое можно показать
export function firstDisplayValue(...values: (string | null | undefined)[]): string | null {
  for (const v of values) {
    const d = displayValue(v);
    if (d) return d;
  }
  return null;
}
