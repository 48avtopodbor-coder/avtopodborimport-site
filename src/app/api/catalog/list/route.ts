import { NextRequest, NextResponse } from "next/server";
import { parseFilters } from "@/lib/catalog-filters";
import { getCatalogList, normalizeCatalogFilters } from "@/lib/catalog-data";
export async function GET(request: NextRequest) {
  try {
    return NextResponse.json(
      await getCatalogList(
        await normalizeCatalogFilters(
          parseFilters(Object.fromEntries(request.nextUrl.searchParams)),
        ),
      ),
    );
  } catch {
    return NextResponse.json({ error: "Не удалось загрузить автомобили" }, { status: 503 });
  }
}
