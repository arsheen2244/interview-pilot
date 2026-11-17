"""
Question retrieval.

v1 (this file): lightweight keyword + tag scoring, zero dependencies, easy to test.
v2 (roadmap):   swap `search` for an embedding search (ChromaDB / pgvector / Qdrant)
                and seed the bank from the candidate's resume + a job description.

Scoring, highest first:
  * topic match   - the question's topic words are all in the query ("AI / RAG" -> topic "ai")
  * tag overlap   - query words that appear in the question's tags / text
  * difficulty    - small bonus when the difficulty matches
The winner is drawn at random from the best few candidates, so repeat sessions differ.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

_WORD = re.compile(r"[a-z0-9+#]+")

TOPIC_WEIGHT = 3.0
DIFFICULTY_BONUS = 0.5
TOP_K = 3


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


class QuestionBank:
    def __init__(self, path: Path, rng: random.Random | None = None) -> None:
        self.questions: list[dict] = json.loads(path.read_text(encoding="utf-8"))
        self._by_id = {q["id"]: q for q in self.questions}
        self._rng = rng or random.Random()

    def get(self, question_id: str) -> dict | None:
        return self._by_id.get(question_id)

    def topics(self) -> list[str]:
        return sorted({q["topic"] for q in self.questions})

    def search(self, topic: str, difficulty: str = "medium", exclude: list[str] | None = None) -> dict | None:
        exclude = set(exclude or [])
        query = _tokens(topic)
        scored: list[tuple[float, dict]] = []
        for q in self.questions:
            if q["id"] in exclude:
                continue
            topic_words = _tokens(q["topic"])
            on_topic = bool(topic_words) and topic_words <= query
            doc = _tokens(" ".join([*q.get("tags", []), q["question"]]))
            overlap = len(query & doc)
            if not on_topic and overlap == 0:
                continue
            score = (TOPIC_WEIGHT if on_topic else 0) + overlap
            score += DIFFICULTY_BONUS if q["difficulty"] == difficulty.lower() else 0
            scored.append((score, q))
        if not scored:
            return None
        scored.sort(key=lambda s: s[0], reverse=True)
        return self._rng.choice([q for _, q in scored[:TOP_K]])
