"""Conservative car title extraction shared by the importer and backfill."""

import re
import unicodedata


YEAR_MARKER = re.compile(r"\s*(?:19|20)\d{2}款(?:\s+|$)")
LATIN_MODEL = re.compile(r"^[A-Za-z][A-Za-z0-9 .+/-]*$")
LATIN_TRIM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .+/-]*$")
TRIM_TOKENS = re.compile(r"[A-Za-z0-9]+(?:[.][0-9]+)?")


def normalize_brand(raw: str) -> str:
    value = unicodedata.normalize("NFKC", raw or "").strip().casefold()
    return re.sub(r"[\s\-_·.]+", "", value)


def model_slug(name: str) -> str:
    value = unicodedata.normalize("NFKC", name).casefold()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def source_series(full_name: str, series_name: str | None) -> str | None:
    if series_name and series_name.strip():
        return series_name.strip()
    match = YEAR_MARKER.search(full_name or "")
    if match:
        return full_name[:match.start()].strip()
    # Some sellers use model/engine/year/trim instead of the standard title.
    if re.search(r"/[^/]+/\d{2}款(?:/|$)", full_name or ""):
        return full_name.split("/", 1)[0].strip()
    return None


def extract_title(
    full_name: str,
    series_name: str | None,
    brand_cn: str | None,
    aliases: dict[str, tuple[str, str]],
    brand_slug: str,
) -> tuple[str | None, str | None, str | None]:
    """Return verified model name, URL slug and limited Latin trim.

    aliases is keyed by the exact Chinese series for the given brand.
    Unknown Chinese series and trims stay NULL. The original full name is untouched.
    """
    source = source_series(full_name, series_name) or (full_name if full_name in aliases else None)
    if not source:
        return None, None, None
    # Che168 may append an import marker to the same model series.
    core_source = re.sub(r"(?:\(进口\)|进口)$", "", source).strip()
    known = aliases.get(full_name) or aliases.get(source) or aliases.get(core_source)
    if known:
        name, slug = known
    else:
        bare = core_source
        if brand_cn and bare.startswith(brand_cn):
            bare = bare[len(brand_cn):].strip()
        if not LATIN_MODEL.fullmatch(bare):
            return None, None, None
        name = bare
        slug = model_slug(name)
        if not slug:
            return None, None, None

    trim = None
    marker = YEAR_MARKER.search(full_name or "")
    if marker:
        tail = full_name[marker.end():].strip()
        # Only the two known patterns are safe to display without translating
        # a Chinese trim name.
        if brand_slug == "jetta":
            code = re.match(r"^(\d{3}TSI)\b", tail)
            pro = re.search(r"Pro\b", tail, re.I)
            if code and pro:
                trim = f"{code.group(1)} Pro"
        elif brand_slug == "li-auto" and re.fullmatch(r"(?:Pro|Max|Ultra)", tail, re.I):
            trim = tail
        elif LATIN_TRIM.fullmatch(tail) and len(TRIM_TOKENS.findall(tail)) <= 3:
            trim = tail
    return name, slug, trim
