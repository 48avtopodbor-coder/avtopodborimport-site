export function usedBrandHref(brand: string, query = "") {
  const params = new URLSearchParams(query);
  params.delete("page");
  if (brand) params.set("brand", brand);
  else params.delete("brand");

  const search = params.toString();
  return search ? `/catalog/used?${search}` : "/catalog/used";
}
