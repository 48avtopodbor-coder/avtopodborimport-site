import type { MetadataRoute } from "next";
import { getCatalogSitemapEntries } from "@/lib/catalog-data";
import { SITE_ORIGIN } from "@/lib/site";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries = await getCatalogSitemapEntries();
  const catalog = `${SITE_ORIGIN}/catalog/used`;
  const brands = new Set(entries.flatMap(({ brand_slug }) => (brand_slug ? [brand_slug] : [])));

  return [
    { url: SITE_ORIGIN + "/" },
    { url: catalog },
    ...Array.from(brands, (brand) => ({ url: `${catalog}?brand=${encodeURIComponent(brand)}` })),
    ...entries.map(({ listing_id }) => ({
      url: `${SITE_ORIGIN}/car/${encodeURIComponent(listing_id)}`,
    })),
  ];
}
