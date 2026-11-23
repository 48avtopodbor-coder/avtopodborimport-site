import { NextRequest, NextResponse } from "next/server";
import { parseFilters } from "@/lib/catalog-filters";
import { getCatalogFacets, normalizeCatalogFilters } from "@/lib/catalog-data";
export async function GET(request: NextRequest) {
  try {
    const f = await normalizeCatalogFilters(
      parseFilters(Object.fromEntries(request.nextUrl.searchParams)),
    );
    return NextResponse.json(await getCatalogFacets(f), {
      headers: { "Cache-Control": "public, max-age=60, stale-while-revalidate=240" },
    });
  } catch {
    return NextResponse.json({ error: "Не удалось загрузить фильтры" }, { status: 503 });
  }
}
