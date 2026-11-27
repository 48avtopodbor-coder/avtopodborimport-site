"""Public seller copy, shared with the server renderer, and translation number checks."""
from collections import Counter
from decimal import Decimal
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata


@lru_cache(maxsize=1)
def content_rules():
    directory = Path(__file__).resolve().parent
    path = directory / "seller-content-rules.json"
    if not path.exists():
        path = directory.parent / "src/lib/seller-content-rules.json"
    return [(rule["kind"], re.compile(rule["pattern"], re.I))
            for rule in json.loads(path.read_text(encoding="utf-8"))]


def clean_seller_text(text, matches=None):
    original = (text or "").strip()
    value = original
    for kind, pattern in content_rules():
        if matches is None:
            value = pattern.sub(" ", value)
            continue

        def remove(match):
            matches.append((kind, match.group()))
            return " "
        value = pattern.sub(remove, value)
    if value == original:
        return original
    lines = []
    for line in value.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        line = re.sub(r"(?:^|(?<=[.!！。]))[ ,，;；:：.!！。—–-]+(?=\S|$)", "", line)
        line = re.sub(r"[ ,，;；:：—–-]+(?=[.!！。]|$)", "", line)
        if re.search(r"[^\s.,，;；:：!?！？。—–\-«»\"()（）]", line):
            lines.append(line)
    return "\n".join(lines).strip()


# A date is compared component by component. Keeping separators prevents grouping
# adjacent date components as thousands (which is valid in Russian prices).
# Listings abbreviate contemporary model/registration years, e.g. 23年宝马.
SHORT_YEAR = re.compile(r"(?<![0-9./-])(2[0-9])(?=[ ?]*(?:改?款|上牌|年))")
MONTH_PATTERN = r"(0?[1-9]|1[0-2])"
SHORT_DATE = r"([12][0-9])[./-]" + MONTH_PATTERN + r"(?:[./-](0?[1-9]|[12][0-9]|3[01]))?(?![0-9./-])"
LABELLED_SHORT_DATE = re.compile(r"(?:出厂|上牌|生产|保险|登记|交强|厂牌|强制险|强险)(?:时间|日期|到期)?[】 :：?]*" + SHORT_DATE)
SHORT_REG_DATE = re.compile(r"(?<![a-zA-Z0-9./-])" + SHORT_DATE + r"(?=[ ?]*(?:出厂|上牌|生产|月))")
GROUPED_COMMA = re.compile(r"(?<![0-9.])[0-9]{1,3}(?:,[0-9]{3})+(?![0-9])")
MONTH_YEAR = re.compile(r"(?<![0-9.])(?:(0?[1-9]|[12][0-9]|3[01])[./-])?(0?[1-9]|1[0-2])[./-]((?:19|20)[0-9]{2})(?![0-9])")
DATE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-./年](0?[1-9]|1[0-2])(?:[-./月](0?[1-9]|[12]\d|3[01]))?(?!\d)")
MONTHS = ("январ", "феврал", "март", "апрел", "ма[йяе]", "июн",
          "июл", "август", "сентябр", "октябр", "ноябр", "декабр")
MONTH_NAME = re.compile(r"\b(?:" + "|".join(f"({stem}[а-я]*)" for stem in MONTHS) + r")\b", re.I)
NUMBER = re.compile(r"(?P<value>[0-9]{1,3}(?:[ \u00a0\u202f][0-9]{3})+(?![0-9])|[0-9]+(?:[.,][0-9]+)?)"
                    r"(?:[ \t?]*(?:多|余|来)?(?P<unit>万|w(?=km)|w(?![a-z0-9])|(?<=[0-9])k(?![a-z0-9?])|千(?!米)|"
                    r"тыс(?:яч(?:а|и|у)?)?\b|млн\b|миллион(?:а|ов)?\b))?", re.I)


def quantities(text):
    text = unicodedata.normalize("NFKC", text.replace("，", ";"))
    text = GROUPED_COMMA.sub(lambda m: m[0].replace(",", ""), text)
    if re.search(r"[一-龥]", text):
        text = re.sub(r"(?<=[一-龥])\?+(?=[一-龥])", "", text)
        def full_date(match):
            return " 20" + "/".join(x for x in match.groups() if x)
        text = LABELLED_SHORT_DATE.sub(full_date, text)
        text = SHORT_REG_DATE.sub(full_date, text)
        # 成 is one tenth of a whole (the usual unit for a down payment).
        text = re.sub(r"([0-9])(?:到|至|-)([0-9])成", lambda m: f"{m[1]}0%-{m[2]}0%", text)
        text = re.sub(r"(?<![0-9.])([0-9])成", r"\g<1>0%", text)
    def year_or_duration(match):
        prefix = text[max(0, match.start() - 8):match.start()].rstrip()
        if re.search(r"(?:保修|质保|长达|使用|服务|深耕|成立|从业|经营|年限|累计|超过|不足)$", prefix):
            return match[0]
        if re.match(r" *年(?:以上|以下|以内|之久|以来|经验|历史|质保)", text[match.end():]):
            return match[0]
        return "20" + match[1]
    text = SHORT_YEAR.sub(year_or_duration, text)
    text = MONTH_YEAR.sub(lambda m: "/".join(x for x in m.groups() if x), text)
    text = DATE.sub(lambda m: "/".join(x for x in m.groups() if x), text)
    text = MONTH_NAME.sub(lambda m: "/" + str(m.lastindex) + "/", text)
    values = Counter()
    for match in NUMBER.finditer(text):
        value = Decimal(match["value"].replace(" ", "").replace(",", "."))
        unit = (match["unit"] or "").lower()
        if unit in ("万", "w"):
            value *= 10000
        elif unit in ("千", "k") or unit.startswith("тыс"):
            value *= 1000
        elif unit:
            value *= 1000000
        values[value] += 1
    return values


def missing_numbers(source, translation):
    missing = quantities(clean_seller_text(source)) - quantities(clean_seller_text(translation))
    return [format(value, "f") for value in sorted(missing.elements())]
