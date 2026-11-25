/** Only link to the matching Che168 listing, never to an arbitrary imported URL. */
export function originalListingUrl(raw: string | null, listingId: string): string | null {
  if (!raw || !/^\d+$/.test(listingId)) return null;
  try {
    const url = new URL(raw);
    if (
      !["https:", "http:"].includes(url.protocol) ||
      !["www.che168.com", "che168.com"].includes(url.hostname) ||
      url.username ||
      url.password ||
      url.port ||
      !url.pathname.endsWith(`/${listingId}.html`)
    )
      return null;
    url.protocol = "https:";
    url.search = "";
    url.hash = "";
    return url.href;
  } catch {
    return null;
  }
}
