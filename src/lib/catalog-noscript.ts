import type { CatalogFilters } from "./catalog-filters";
import type { Facets } from "./catalog-data";

function escapeHtml(value: string | number) {
  return String(value).replace(/[&<>"']/g, (char) => {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]!;
  });
}

// Keep noscript content in one static chunk: streamed React placeholders inside
// it are inert when scripting is enabled, so completion scripts cannot find them.
export function catalogNoScriptForm(filters: CatalogFilters, facets: Facets) {
  const options = (items: Facets["brands"], selected: string[]) =>
    items
      .map(
        (item) =>
          `<option value="${escapeHtml(item.slug)}"${selected.includes(item.slug) ? " selected" : ""}>${escapeHtml(item.name)}</option>`,
      )
      .join("");
  return `<form action="/catalog/used" class="mb-6 flex flex-wrap gap-3 rounded-xl bg-graphite-800 p-4 text-sm text-white">
    <label>Марка <select name="brand" class="ml-2 min-h-11 bg-graphite-900"><option value="">Все марки</option>${options(facets.brands, [filters.brand])}</select></label>
    ${filters.brand ? `<label>Модели <select multiple name="model" class="ml-2 bg-graphite-900">${options(facets.models, filters.models)}</select></label>` : ""}
    <label>Год от <input name="yearFrom" type="number" value="${escapeHtml(filters.yearFrom ?? "")}" class="ml-2 min-h-11 w-24 bg-graphite-900"></label>
    <label>Пробег до <input name="mileageTo" type="number" value="${escapeHtml(filters.mileageTo ?? "")}" class="ml-2 min-h-11 w-28 bg-graphite-900"></label>
    <button class="min-h-11 rounded-lg bg-orange-500 px-4 text-black">Применить фильтры</button>
  </form>`;
}
