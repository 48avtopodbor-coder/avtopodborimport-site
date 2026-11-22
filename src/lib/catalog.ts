export function usedBrandHref(brand: string, query = "") {
  const params = new URLSearchParams(query);
  params.delete("page");
  params.delete("model");
  if (brand) params.set("brand", brand);
  else params.delete("brand");

  const search = params.toString();
  return search ? `/catalog/used?${search}` : "/catalog/used";
}
