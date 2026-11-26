import type { MetadataRoute } from "next";
import { getCatalogSitemapEntries } from "@/lib/catalog-data";
import { SITE_ORIGIN } from "@/lib/site";

export const revalidate = 0;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { listingIds, brandSlugs } = await getCatalogSitemapEntries();
  const catalog = `${SITE_ORIGIN}/catalog/used`;

  return [
    { url: SITE_ORIGIN + "/" },
    { url: catalog },
    ...brandSlugs.map((brand) => ({ url: `${catalog}?brand=${encodeURIComponent(brand)}` })),
    ...listingIds.map((listing_id) => ({
      url: `${SITE_ORIGIN}/car/${encodeURIComponent(listing_id)}`,
    })),
  ];
}
