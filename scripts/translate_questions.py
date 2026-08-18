"""Translate the enriched question bank to Traditional Chinese with a resume cache.

Run with:

    uv run --with deep-translator --with opencc-python-reimplemented python scripts/translate_questions.py
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from pathlib import Path

from deep_translator import GoogleTranslator
from opencc import OpenCC


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "questions.enriched.json"
OUTPUT = ROOT / "data" / "questions.json"
CACHE_FILE = ROOT / "data" / "translations.zh-TW.cache.json"
MAX_PART_LENGTH = 3200
MAX_BATCH_LENGTH = 4300


def split_text(text: str, limit: int = MAX_PART_LENGTH) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            parts.append(remaining)
            break
        cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    return parts


def cache_key(field_key: str, source: str) -> str:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"{field_key}:{digest}"


def normalize_zh(value: str, converter: OpenCC) -> str:
    value = converter.convert(value)
    replacements = {
        "控製": "控制",
        "匹配": "符合",
        "默認": "預設",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return value


def translate_batch(translator: GoogleTranslator, jobs: list[dict]) -> dict[str, str]:
    payload = "\n".join(f"<<<{job['token']}>>>\n{job['text']}" for job in jobs)
    for attempt in range(4):
        try:
            translated = translator.translate(payload)
            matches = list(re.finditer(r"<<<(T\d{7})>>>", translated))
            values: dict[str, str] = {}
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(translated)
                values[match.group(1)] = translated[match.end() : end].strip()
            if len(values) == len(jobs):
                return values
        except Exception:
            if attempt == 3:
                raise
        time.sleep(1.5 * (attempt + 1))

    # Marker parsing failed. Translate each part separately rather than losing data.
    return {job["token"]: translator.translate(job["text"]) for job in jobs}


def main() -> None:
    questions = json.loads(INPUT.read_text(encoding="utf-8"))
    cache = (
        json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if CACHE_FILE.exists()
        else {}
    )

    fields: list[tuple[str, str]] = []
    traditional_taiwan = OpenCC("s2twp")
    for question in questions:
        prefix = str(question["id"])
        fields.append((f"{prefix}.question", question["question"]))
        fields.extend(
            (f"{prefix}.option.{index}", option)
            for index, option in enumerate(question["options"])
        )
        fields.append((f"{prefix}.explanation", question["explanationEn"]))

    jobs: list[dict] = []
    token_number = 0
    field_parts: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for field_key, source in fields:
        key = cache_key(field_key, source)
        if key in cache:
            continue
        for part_index, part in enumerate(split_text(source)):
            token_number += 1
            token = f"T{token_number:07d}"
            jobs.append(
                {
                    "token": token,
                    "fieldKey": field_key,
                    "cacheKey": key,
                    "partIndex": part_index,
                    "text": part,
                }
            )
            field_parts[key].append((part_index, token))

    batches: list[list[dict]] = []
    current: list[dict] = []
    current_length = 0
    for job in jobs:
        cost = len(job["text"]) + 20
        if current and current_length + cost > MAX_BATCH_LENGTH:
            batches.append(current)
            current = []
            current_length = 0
        current.append(job)
        current_length += cost
    if current:
        batches.append(current)

    print(
        f"Translation fields={len(fields)} cached={len(fields) - len(field_parts)} "
        f"jobs={len(jobs)} batches={len(batches)}",
        flush=True,
    )
    translator = GoogleTranslator(source="en", target="zh-TW")
    translated_parts: dict[str, str] = {}
    for batch_index, batch in enumerate(batches, 1):
        values = translate_batch(translator, batch)
        translated_parts.update(values)

        completed_keys = {
            job["cacheKey"]
            for job in batch
            if all(
                token in translated_parts
                for _, token in field_parts[job["cacheKey"]]
            )
        }
        for key in completed_keys:
            ordered = sorted(field_parts[key])
            cache[key] = " ".join(translated_parts[token] for _, token in ordered)
        CACHE_FILE.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if batch_index == 1 or batch_index % 10 == 0 or batch_index == len(batches):
            print(f"Translated batch {batch_index}/{len(batches)}", flush=True)

    for question in questions:
        prefix = str(question["id"])
        question["questionZh"] = normalize_zh(cache[
            cache_key(f"{prefix}.question", question["question"])
        ], traditional_taiwan)
        question["optionsZh"] = [
            normalize_zh(cache[cache_key(f"{prefix}.option.{index}", option)], traditional_taiwan)
            for index, option in enumerate(question["options"])
        ]
        question["explanation"] = normalize_zh(cache[
            cache_key(f"{prefix}.explanation", question["explanationEn"])
        ], traditional_taiwan)
        question["translationStatus"] = "machine-translated-zh-TW"

    OUTPUT.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(questions)} translated questions to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
