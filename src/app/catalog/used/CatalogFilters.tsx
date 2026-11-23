"use client";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";
import { createPortal } from "react-dom";
import CatalogBrandLogo from "./CatalogBrandLogo";
import { useRouter } from "next/navigation";
import {
  BODY_NAMES,
  SORT_NAMES,
  activeFilterCount,
  catalogHref,
  emptyFilters,
  filterParams,
  type CatalogFilters as Filters,
} from "@/lib/catalog-filters";
import type { Facets } from "@/lib/catalog-data";

type Panel = "brand" | "body" | "year" | "price" | "mileage" | "mobile";
const labels = {
  brand: "Марка и модель",
  body: "Кузов",
  year: "Год",
  price: "Цена, ₽",
  mileage: "Пробег",
  mobile: "Фильтры",
};
const focusable =
  'button:not(:disabled), input:not(:disabled), select:not(:disabled), a[href], [tabindex="0"]';
function Chevron({ expanded }: { expanded: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`ml-2 inline-block transition-transform ${expanded ? "rotate-180" : ""}`}
    >
      ⌄
    </span>
  );
}
function NumericRange({
  title,
  from,
  to,
  onChange,
  disabled = false,
  min,
  max,
}: {
  title: string;
  from?: number;
  to?: number;
  onChange: (key: "from" | "to", value?: number) => void;
  disabled?: boolean;
  min?: number;
  max?: number;
}) {
  return (
    <fieldset disabled={disabled} className="min-w-0">
      <legend className="mb-3 text-sm text-gray-400">{title}</legend>
      <div className="grid grid-cols-2 gap-3">
        {(["from", "to"] as const).map((key) => (
          <label key={key} className="min-w-0 text-xs text-gray-400">
            {key === "from" ? "От" : "До"}
            <input
              type="number"
              inputMode="numeric"
              min={min ?? 0}
              max={max}
              value={(key === "from" ? from : to) ?? ""}
              onChange={(e) =>
                onChange(key, e.target.value === "" ? undefined : Number(e.target.value))
              }
              className="mt-1 min-h-11 w-full min-w-0 rounded-lg border border-white/15 bg-graphite-900 px-3 text-base text-white outline-none focus:border-orange-500 disabled:opacity-50"
            />
          </label>
        ))}
      </div>
    </fieldset>
  );
}
function FilterControls({ filters, initialFacets }: { filters: Filters; initialFacets: Facets }) {
  const router = useRouter();
  const [open, setOpen] = useState<Panel | null>(null);
  const [draft, setDraft] = useState(filters);
  const [facets, setFacets] = useState(initialFacets);
  const [facetsBrand, setFacetsBrand] = useState(filters.brand);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [search, setSearch] = useState("");
  const [sections, setSections] = useState<string[]>(["brand"]);
  const [navigating, startTransition] = useTransition();
  const root = useRef<HTMLDivElement>(null),
    panel = useRef<HTMLDivElement>(null),
    opener = useRef<HTMLElement | null>(null);
  const touchY = useRef<number | null>(null);
  const close = useCallback(() => {
    setOpen(null);
    requestAnimationFrame(() => opener.current?.focus());
  }, []);
  const draftKey = filterParams(draft, false).toString();
  useEffect(() => {
    if (!open) return;
    const abort = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/catalog/facets?${draftKey}`, { signal: abort.signal });
        if (!response.ok) throw new Error("facets");
        const data: Facets = await response.json();
        setFacets(data);
        setFacetsBrand(draft.brand);
        setLoading(false);
      } catch (e) {
        if (!(e instanceof DOMException && e.name === "AbortError")) {
          setError(true);
          setLoading(false);
        }
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [draftKey, draft.brand, open, retry]);
  useEffect(() => {
    if (!open) return;
    const active = panel.current;
    const first = active?.querySelector<HTMLElement>(focusable);
    first?.focus();
    const outside = (e: PointerEvent) => {
      const target = e.target as Node;
      if (!root.current?.contains(target) && !panel.current?.contains(target)) close();
    };
    const keys = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      }
      if (open === "mobile" && e.key === "Tab" && active) {
        const nodes = [...active.querySelectorAll<HTMLElement>(focusable)].filter(
          (n) => n.getClientRects().length > 0,
        );
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", keys);
    const saved = document.body.style.cssText;
    const y = window.scrollY;
    if (open === "mobile") {
      document.body.style.position = "fixed";
      document.body.style.top = `-${y}px`;
      document.body.style.width = "100%";
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", keys);
      if (open === "mobile") {
        document.body.style.cssText = saved;
        window.scrollTo(0, y);
      }
    };
  }, [open, close]);
  useEffect(() => {
    const change = () => close();
    window.addEventListener("popstate", change);
    return () => window.removeEventListener("popstate", change);
  }, [close]);
  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    media.addEventListener("change", close);
    return () => media.removeEventListener("change", close);
  }, [close]);
  function editDraft(update: React.SetStateAction<Filters>) {
    setDraft(update);
    setLoading(true);
    setError(false);
  }
  function toggle(key: Panel, target: HTMLElement) {
    if (open === key) {
      close();
      return;
    }
    opener.current = target;
    editDraft(filters);
    setFacets(initialFacets);
    setSearch("");
    setError(false);
    setOpen(key);
  }
  function apply(value = draft) {
    close();
    startTransition(() => router.push(catalogHref({ ...value, page: 1 }), { scroll: false }));
  }
  function number(key: "year" | "price" | "mileage", end: "from" | "to", value?: number) {
    const field = `${key}${end === "from" ? "From" : "To"}` as
      "yearFrom" | "yearTo" | "priceFrom" | "priceTo" | "mileageFrom" | "mileageTo";
    editDraft((d) => ({ ...d, [field]: value }));
  }
  function toggleValue(key: "models" | "bodies", value: string) {
    editDraft((d) => ({
      ...d,
      [key]: d[key].includes(value) ? d[key].filter((v) => v !== value) : [...d[key], value],
    }));
  }
  const invalidRange = (["year", "price", "mileage"] as const).some((k) => {
    const from = draft[`${k}From`],
      to = draft[`${k}To`];
    return (
      (from !== undefined && (!Number.isSafeInteger(from) || from < 0)) ||
      (to !== undefined && (!Number.isSafeInteger(to) || to < 0)) ||
      (from !== undefined && to !== undefined && from > to)
    );
  });
  const brand = initialFacets.brands.find((b) => b.slug === filters.brand);
  const draftBrand =
    facets.brands.find((b) => b.slug === draft.brand) ||
    initialFacets.brands.find((b) => b.slug === draft.brand);
  const pill =
    "flex min-h-11 items-center justify-center rounded-full border px-4 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500";
  const choice = (selected: boolean) =>
    `min-h-11 rounded-lg border px-3 py-2 text-sm ${selected ? "border-orange-500 bg-orange-500 text-black" : "border-white/10 bg-graphite-900 text-gray-200 hover:border-gray-400"}`;
  const brandContent = (
    <div className="grid gap-5 lg:grid-cols-[minmax(220px,0.8fr)_2fr]">
      <div className="min-w-0">
        <label className="mb-2 block text-sm text-gray-400">
          Поиск марки
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Например, Mazda"
            className="mt-2 min-h-11 w-full rounded-lg border border-white/15 bg-graphite-900 px-3 text-base text-white outline-none focus:border-orange-500"
          />
        </label>
        <div
          className="max-h-64 overflow-y-auto overscroll-contain"
          role="group"
          aria-label="Марки"
        >
          {facets.brands
            .filter((b) => b.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
            .map((b) => (
              <button
                key={b.slug}
                type="button"
                aria-pressed={draft.brand === b.slug}
                onClick={() => editDraft((d) => ({ ...d, brand: b.slug, models: [] }))}
                onKeyDown={(e) => {
                  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                    e.preventDefault();
                    const nodes = [
                      ...e.currentTarget.parentElement!.querySelectorAll<HTMLButtonElement>(
                        "button",
                      ),
                    ];
                    nodes[
                      (nodes.indexOf(e.currentTarget) +
                        (e.key === "ArrowDown" ? 1 : nodes.length - 1)) %
                        nodes.length
                    ]?.focus();
                  }
                }}
                className={`flex min-h-11 w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm ${draft.brand === b.slug ? "bg-orange-500/10 text-orange-400" : "text-gray-200 hover:bg-white/5"}`}
              >
                <CatalogBrandLogo brand={b} />
                <span className="min-w-0 flex-1 break-words">{b.name}</span>
                <span className="tabular-nums text-gray-400">{b.count.toLocaleString("ru")}</span>
                <span aria-hidden="true">›</span>
              </button>
            ))}
        </div>
      </div>
      <div className="min-w-0">
        <div className="mb-3 text-sm text-gray-400">
          {draftBrand ? `Модели ${draftBrand.name}` : "Модели"}
        </div>
        {!draft.brand ? (
          <p className="text-sm text-gray-400">Выберите марку, чтобы увидеть модели.</p>
        ) : (
          <>
            <button
              type="button"
              aria-pressed={!draft.models.length}
              onClick={() => editDraft((d) => ({ ...d, models: [] }))}
              className={choice(!draft.models.length)}
            >
              Все модели
            </button>
            <div
              className="mt-3 flex max-h-72 flex-wrap gap-2 overflow-y-auto overscroll-contain"
              aria-busy={loading}
            >
              {(!loading || facetsBrand === draft.brand) &&
                facets.models.map((m) => (
                  <button
                    key={m.slug}
                    type="button"
                    aria-pressed={draft.models.includes(m.slug)}
                    onClick={() => toggleValue("models", m.slug)}
                    className={choice(draft.models.includes(m.slug))}
                  >
                    {m.name} <span className="ml-1 tabular-nums opacity-75">{m.count}</span>
                  </button>
                ))}
              {loading && facetsBrand !== draft.brand && (
                <p role="status" className="min-h-11 text-sm text-gray-400">
                  Загружаем модели…
                </p>
              )}
              {!loading && !facets.models.length && (
                <p className="text-sm text-gray-400">Нет моделей с выбранными условиями.</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
  const bodyContent = (
    <div className="flex flex-wrap gap-2">
      {Object.entries(BODY_NAMES).map(([slug, name]) => {
        const count = facets.bodies.find((b) => b.slug === slug)?.count || 0;
        return (
          <label
            key={slug}
            className={`${choice(draft.bodies.includes(slug))} flex cursor-pointer items-center gap-2`}
          >
            <input
              type="checkbox"
              checked={draft.bodies.includes(slug)}
              onChange={() => toggleValue("bodies", slug)}
              className="size-4 accent-orange-500"
            />
            {name}
            <span className="tabular-nums opacity-75">{count}</span>
          </label>
        );
      })}
    </div>
  );
  const yearContent = (
    <NumericRange
      title="Год"
      from={draft.yearFrom}
      to={draft.yearTo}
      min={1900}
      max={new Date().getFullYear() + 1}
      onChange={(end, value) => number("year", end, value)}
    />
  );
  const priceContent = (
    <>
      <NumericRange
        title="Цена, ₽"
        from={draft.priceFrom}
        to={draft.priceTo}
        disabled={!facets.priceAvailable}
        onChange={(end, value) => number("price", end, value)}
      />
      {!facets.priceAvailable && (
        <p className="mt-3 max-w-lg text-sm text-gray-400">
          Фильтр станет доступен после подключения расчёта рублёвой цены.
        </p>
      )}
    </>
  );
  const mileageContent = (
    <>
      <NumericRange
        title="Пробег, км"
        from={draft.mileageFrom}
        to={draft.mileageTo}
        max={3000000}
        onChange={(end, value) => number("mileage", end, value)}
      />
      <div className="mt-3 flex flex-wrap gap-2">
        {[30000, 60000, 100000].map((v) => (
          <button
            type="button"
            key={v}
            className={choice(draft.mileageTo === v && !draft.mileageFrom)}
            onClick={() => editDraft((d) => ({ ...d, mileageFrom: undefined, mileageTo: v }))}
          >
            До {v / 1000} тыс. км
          </button>
        ))}
      </div>
    </>
  );
  const content = {
    brand: brandContent,
    body: bodyContent,
    year: yearContent,
    price: priceContent,
    mileage: mileageContent,
  };
  const footer = (
    <div className="border-t border-white/10 px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-4 sm:px-6">
      {invalidRange && (
        <p role="alert" className="mb-3 text-sm text-orange-400">
          Проверьте диапазон: значение «от» должно быть меньше «до».
        </p>
      )}
      {error && (
        <p role="alert" className="mb-3 text-sm text-gray-200">
          Не удалось обновить количество.{" "}
          <button
            type="button"
            className="min-h-11 underline"
            onClick={() => {
              setLoading(true);
              setError(false);
              setRetry((r) => r + 1);
            }}
          >
            Повторить
          </button>
        </p>
      )}
      <button
        type="button"
        onClick={() => apply()}
        disabled={loading || error || invalidRange || navigating}
        className="min-h-12 w-full rounded-lg bg-orange-500 px-5 py-3 text-sm font-bold text-black disabled:opacity-60 lg:w-auto lg:min-w-52"
        aria-live="polite"
      >
        {loading
          ? "Считаем автомобили…"
          : navigating
            ? "Открываем каталог…"
            : `Показать ${facets.total.toLocaleString("ru")} авто`}
      </button>
    </div>
  );
  const chips: { key: string; text: string; next: Filters }[] = [];
  if (filters.brand)
    chips.push({
      key: "brand",
      text: brand?.name || filters.brand,
      next: { ...filters, brand: "", models: [] },
    });
  for (const model of filters.models)
    chips.push({
      key: `model-${model}`,
      text: initialFacets.models.find((m) => m.slug === model)?.name || model,
      next: { ...filters, models: filters.models.filter((m) => m !== model) },
    });
  for (const body of filters.bodies)
    chips.push({
      key: body,
      text: BODY_NAMES[body],
      next: { ...filters, bodies: filters.bodies.filter((b) => b !== body) },
    });
  for (const k of ["year", "price", "mileage"] as const)
    if (filters[`${k}From`] !== undefined || filters[`${k}To`] !== undefined)
      chips.push({
        key: k,
        text: `${labels[k]}: ${filters[`${k}From`] !== undefined ? `от ${filters[`${k}From`]!.toLocaleString("ru")}` : ""} ${filters[`${k}To`] !== undefined ? `до ${filters[`${k}To`]!.toLocaleString("ru")}` : ""}`,
        next: { ...filters, [`${k}From`]: undefined, [`${k}To`]: undefined },
      });
  if (filters.fuel)
    chips.push({
      key: "fuel",
      text: filters.fuel,
      next: { ...filters, fuel: undefined },
    });
  const sortControl = (
    <label className="relative min-w-0">
      <span className="sr-only">Сортировка</span>
      <select
        aria-label="Сортировка"
        value={filters.sort}
        onChange={(e) => apply({ ...filters, sort: e.target.value as Filters["sort"] })}
        className="min-h-11 max-w-full rounded-full border border-white/10 bg-graphite-800 py-2 pl-4 pr-7 text-sm text-gray-200 outline-none focus:border-orange-500"
      >
        {Object.entries(SORT_NAMES).map(([value, name]) => (
          <option key={value} value={value}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <div ref={root} className="mb-6 font-body">
      <div className="hidden flex-wrap items-center gap-2 lg:flex">
        {(["brand", "body", "year", "price", "mileage"] as const).map((key) => {
          const active =
            key === "brand"
              ? Boolean(filters.brand)
              : key === "body"
                ? filters.bodies.length > 0
                : filters[`${key}From`] !== undefined || filters[`${key}To`] !== undefined;
          return (
            <button
              type="button"
              key={key}
              onClick={(e) => toggle(key, e.currentTarget)}
              aria-expanded={open === key}
              aria-controls="catalog-filter-panel"
              className={`${pill} ${active || open === key ? "border-orange-500 text-orange-400" : "border-white/10 bg-graphite-800 text-gray-200"}`}
            >
              <span className="max-w-52 truncate">
                {key === "brand" && brand
                  ? `${brand.name}${filters.models.length === 1 ? " · " + (initialFacets.models.find((m) => m.slug === filters.models[0])?.name || filters.models[0]) : filters.models.length ? " · " + filters.models.length : ""}`
                  : labels[key]}
              </span>
              <Chevron expanded={open === key} />
            </button>
          );
        })}
        <div className="ml-auto">{sortControl}</div>
      </div>
      <div className="flex items-center gap-2 lg:hidden">
        <button
          type="button"
          onClick={(e) => toggle("mobile", e.currentTarget)}
          aria-expanded={open === "mobile"}
          aria-controls="catalog-filter-panel"
          className={`${pill} shrink-0 ${activeFilterCount(filters) ? "border-orange-500 text-orange-400" : "border-white/10 bg-graphite-800 text-white"}`}
        >
          ☷ Фильтры{activeFilterCount(filters) ? ` · ${activeFilterCount(filters)}` : ""}
        </button>
        <div className="min-w-0 flex-1">{sortControl}</div>
      </div>
      {open && open !== "mobile" && (
        <div
          id="catalog-filter-panel"
          ref={panel}
          role="dialog"
          aria-label={labels[open]}
          className="mt-3 hidden overflow-hidden rounded-xl border border-white/10 bg-graphite-800 lg:block"
        >
          <div className="flex items-center justify-between px-6 pt-4">
            <h2 className="font-semibold text-white">{labels[open]}</h2>
            <button
              type="button"
              aria-label="Закрыть фильтр"
              onClick={close}
              className="size-11 text-xl text-gray-200"
            >
              ×
            </button>
          </div>
          <div className="p-6">{content[open]}</div>
          {footer}
        </div>
      )}
      {chips.length > 0 && (
        <div
          className="mt-3 flex min-h-11 items-center gap-2 overflow-x-auto pb-1 lg:flex-wrap"
          aria-label="Активные фильтры"
        >
          {chips.map((c) => (
            <button
              type="button"
              key={c.key}
              onClick={() => apply(c.next)}
              aria-label={`Убрать фильтр ${c.text}`}
              className="flex min-h-11 shrink-0 items-center gap-2 rounded-full bg-orange-500/10 px-3 text-sm text-orange-400"
            >
              {c.text}
              <span aria-hidden="true">×</span>
            </button>
          ))}
          <button
            type="button"
            className="min-h-11 shrink-0 px-2 text-sm text-gray-400 underline"
            onClick={() => apply({ ...emptyFilters(), sort: filters.sort })}
          >
            Сбросить всё
          </button>
        </div>
      )}
      {navigating && (
        <p role="status" className="mt-2 text-sm text-gray-400">
          Обновляем каталог…
        </p>
      )}
      {open === "mobile" &&
        createPortal(
          <div
            className="fixed inset-0 z-[100] flex items-end justify-center bg-black/70"
            onPointerDown={(e) => {
              if (e.target === e.currentTarget) close();
            }}
          >
            <div
              id="catalog-filter-panel"
              ref={panel}
              role="dialog"
              aria-modal="true"
              aria-labelledby="mobile-filter-title"
              className="flex max-h-[85dvh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl border border-white/10 bg-graphite-800 text-white"
            >
              <div
                className="flex h-8 shrink-0 items-center justify-center"
                style={{ touchAction: "none" }}
                onPointerDown={(e) => {
                  touchY.current = e.clientY;
                  e.currentTarget.setPointerCapture(e.pointerId);
                }}
                onPointerUp={(e) => {
                  if (touchY.current !== null && e.clientY - touchY.current > 65) close();
                  touchY.current = null;
                }}
              >
                <span className="h-1 w-10 rounded-full bg-gray-600" />
              </div>
              <div className="flex shrink-0 items-center gap-2 px-4 pb-3">
                <h2 id="mobile-filter-title" className="flex-1 font-heading text-base font-bold">
                  Фильтры
                </h2>
                <button
                  type="button"
                  className="min-h-11 px-2 text-sm text-gray-400"
                  onClick={() => editDraft({ ...emptyFilters(), sort: filters.sort })}
                >
                  Сбросить
                </button>
                <button
                  type="button"
                  onClick={close}
                  aria-label="Закрыть фильтры"
                  className="size-11 text-2xl"
                >
                  ×
                </button>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4">
                {(["brand", "body", "price", "year"] as const).map((key) => (
                  <section key={key} className="border-t border-white/10">
                    <button
                      type="button"
                      aria-expanded={sections.includes(key)}
                      aria-controls={`mobile-${key}`}
                      onClick={() =>
                        setSections((s) =>
                          s.includes(key) ? s.filter((v) => v !== key) : [...s, key],
                        )
                      }
                      className="flex min-h-12 w-full items-center justify-between text-left text-sm text-gray-200"
                    >
                      <span>
                        {key === "brand"
                          ? `Марка${draftBrand ? " · " + draftBrand.name : ""}`
                          : key === "year"
                            ? "Год и пробег"
                            : labels[key]}
                      </span>
                      <Chevron expanded={sections.includes(key)} />
                    </button>
                    {sections.includes(key) && (
                      <div id={`mobile-${key}`} className="pb-5">
                        {content[key]}
                        {key === "year" && <div className="mt-5">{mileageContent}</div>}
                      </div>
                    )}
                  </section>
                ))}
              </div>
              {footer}
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}

export default function CatalogFilters(props: { filters: Filters; initialFacets: Facets }) {
  return <FilterControls key={filterParams(props.filters).toString()} {...props} />;
}
