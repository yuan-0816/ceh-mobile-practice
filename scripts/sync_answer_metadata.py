"""Sync PDF-derived answer metadata into the published question bank."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "questions.enriched.json"
TARGET = ROOT / "data" / "questions.json"
ANSWER_FIELDS = (
    "correctIndex",
    "answerText",
    "answerStatus",
    "answerMatchScore",
)


def main() -> None:
    source_questions = json.loads(SOURCE.read_text(encoding="utf-8"))
    published_questions = json.loads(TARGET.read_text(encoding="utf-8"))
    source_by_id = {question["id"]: question for question in source_questions}

    synced = 0
    for question in published_questions:
        source = source_by_id.get(question["id"])
        if source is None:
            continue
        for field in ANSWER_FIELDS:
            if field in source:
                question[field] = source[field]
        question.pop("answerLetter", None)
        question.pop("sourceAnswerText", None)
        synced += 1

    TARGET.write_text(
        json.dumps(published_questions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Synced answer metadata for {synced} questions")


if __name__ == "__main__":
    main()