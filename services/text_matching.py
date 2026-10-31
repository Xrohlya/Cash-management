"""Conservative typo matching; income suggestions never post money themselves."""
import re

from rapidfuzz import fuzz, process
from rapidfuzz.distance import DamerauLevenshtein


def normalized(value):
    return " ".join(re.findall(r"\w+", value.casefold().replace("ё", "е")))


def income_hint(text):
    text = re.sub(r"^(получил[а]?|зарплата|доход|пришл[оа]|получение)\b", "", text, flags=re.I)
    text = re.sub(r"\d(?:[\d \u00a0]*\d)?(?:[.,]\d{1,2})?", " ", text, count=1)
    text = re.sub(r"(?:₽|\bруб(?:ль|ля|лей)?\b)", " ", text, flags=re.I)
    return re.sub(r"^(?:(?:от|из|в|источник)\s+)+", "", normalized(text)).strip()


def income_suggestions(text, sources):
    hint = income_hint(text)
    if not hint:
        return []
    active = [source for source in sources if int(source["active"])]
    choices = [normalized(source["name"]) for source in active]
    return [active[index] for _, _, index in process.extract(
        hint, choices, scorer=fuzz.WRatio, score_cutoff=75, limit=3,
    )]


def category_suggestion(description, aliases):
    query = normalized(description)
    if len(query) < 4 or len(query.split()) > 2:
        return None
    scores = {}
    for alias, score, _ in process.extract(query, list(aliases), scorer=fuzz.ratio,
                                         score_cutoff=75, limit=None):
        distance = DamerauLevenshtein.distance(query, alias)
        if distance > (1 if len(query) <= 5 else 2) or len(query) > 5 and score < 85:
            continue
        category = aliases[alias]
        scores[category] = max(scores.get(category, 0), score)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked or len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 10:
        return None
    return ranked[0][0]
