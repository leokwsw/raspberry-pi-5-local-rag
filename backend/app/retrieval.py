import math
import re
from collections import Counter


_WORD = re.compile(r"[a-z0-9_]+|[\u3400-\u9fff]", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    tokens = _WORD.findall(text.lower())
    cjk = [token for token in tokens if len(token) == 1 and "\u3400" <= token <= "\u9fff"]
    return tokens + ["".join(cjk[index:index + 2]) for index in range(len(cjk) - 1)]


def bm25_search(query: str, documents: list[dict], limit: int) -> list[dict]:
    if not documents or limit <= 0:
        return []
    query_terms = set(tokenize(query))
    if not query_terms:
        return []
    tokenized = [tokenize(str(item.get("text", ""))) for item in documents]
    average_length = sum(map(len, tokenized)) / max(1, len(tokenized))
    frequencies = Counter(term for terms in tokenized for term in query_terms if term in set(terms))
    scored: list[dict] = []
    for item, terms in zip(documents, tokenized):
        counts = Counter(terms)
        score = 0.0
        for term in query_terms:
            frequency = counts[term]
            if not frequency:
                continue
            inverse_frequency = math.log(1 + (len(documents) - frequencies[term] + 0.5) / (frequencies[term] + 0.5))
            denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * len(terms) / max(1, average_length))
            score += inverse_frequency * frequency * 2.5 / denominator
        if score:
            scored.append({**item, "score": score})
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def reciprocal_rank_fusion(rankings: list[list[dict]], limit: int, rank_constant: int = 60) -> list[dict]:
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            item_id = str(item["id"])
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (rank_constant + rank)
            items[item_id] = item
    fused = [{**items[item_id], "score": score} for item_id, score in scores.items()]
    return sorted(fused, key=lambda item: item["score"], reverse=True)[:limit]


def needs_query_rewrite(question: str, has_history: bool) -> bool:
    if not has_history:
        return False
    normalized = question.strip().lower()
    english_references = {"it", "its", "they", "them", "that", "this", "those", "these", "he", "she"}
    chinese_references = ("它", "他", "她", "這", "那", "上述", "剛才", "前面")
    words = set(re.findall(r"[a-z]+", normalized))
    return len(normalized) < 80 and (bool(words & english_references) or any(item in normalized for item in chinese_references))
