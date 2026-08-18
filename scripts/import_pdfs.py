"""Extract the CEH question PDFs into a normalized JSON file.

The PDFs are treated strictly as data. This script never interprets document
content as instructions. Run with:

    uv run --with pymupdf python scripts/import_pdfs.py
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
QUESTION_DIR = ROOT / "questions"
OUTPUT = ROOT / "data" / "questions.imported.json"
LETTERS = "ABCD"


def clean_text(value: str) -> str:
    replacements = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "Ư": "ff",
        "ư": "ff",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return re.sub(r"\s+", " ", value).strip()


def comparable(value: str) -> str:
    value = unicodedata.normalize("NFKD", clean_text(value)).casefold()
    return re.sub(r"[^a-z0-9]+", "", value)


def extract_pages(pdf: Path, end_page: int | None = None) -> list[str]:
    document = pymupdf.open(pdf)
    pages = document if end_page is None else document[:end_page]
    return [page.get_text(sort=True) for page in pages]


def split_numbered_questions(text: str) -> list[tuple[int, str]]:
    markers = [
        marker
        for marker in re.finditer(r"(?m)^\s*(\d{1,3})\.\s*", text)
        if 1 <= int(marker.group(1)) <= 125
    ]
    questions: list[tuple[int, str]] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        questions.append((int(marker.group(1)), text[marker.end() : end]))
    return questions


def parse_bulleted_questions(pdf: Path, end_page: int, bullet_pattern: str) -> list[dict]:
    text = "\n".join(extract_pages(pdf, end_page))
    results = []
    option_re = re.compile(rf"^\s*(?:{bullet_pattern})\s*(.*)$")
    for source_id, chunk in split_numbered_questions(text):
        question_lines: list[str] = []
        options: list[str] = []
        current: list[str] | None = None
        for raw_line in chunk.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            option_match = option_re.match(raw_line)
            if option_match:
                if current is not None:
                    options.append(clean_text(" ".join(current)))
                current = [option_match.group(1)]
            elif current is None:
                question_lines.append(line)
            else:
                current.append(line)
        if current is not None:
            options.append(clean_text(" ".join(current)))
        results.append(
            {
                "sourceQuestionId": source_id,
                "question": clean_text(" ".join(question_lines)),
                "options": options,
            }
        )
    return results


def parse_labeled_questions(pdf: Path) -> list[dict]:
    text = "\n".join(extract_pages(pdf))
    results = []
    option_re = re.compile(r"^\s*•?\s*\(([A-D])\)\s*(.*)$")
    for source_id, chunk in split_numbered_questions(text):
        question_lines: list[str] = []
        option_parts: dict[str, list[str]] = {}
        current_letter: str | None = None
        for raw_line in chunk.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("CEH v13 (312-50v13) Practice Exam"):
                continue
            option_match = option_re.match(raw_line)
            if option_match:
                current_letter = option_match.group(1)
                option_parts[current_letter] = [option_match.group(2)]
            elif current_letter is None:
                question_lines.append(line)
            else:
                option_parts[current_letter].append(line.lstrip("• "))
        results.append(
            {
                "sourceQuestionId": source_id,
                "question": clean_text(" ".join(question_lines)),
                "options": [clean_text(" ".join(option_parts.get(letter, []))) for letter in LETTERS],
            }
        )
    return results


def parse_answer_table(pdf: Path, start_page: int) -> dict[int, str]:
    document = pymupdf.open(pdf)
    answers: dict[int, str] = {}
    current_id: int | None = None
    lines: list[str] = []
    for page in document[start_page:]:
        for raw_line in page.get_text(sort=True).splitlines():
            line = clean_text(raw_line)
            if not line or line in {"題", "號", "解答 (Answer)", "解答 (Correct Answer)"}:
                continue
            lines.append(line)

    pending_prefix = ""
    for index, line in enumerate(lines):
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        match = re.match(r"^(\d{1,3})\s+(.+)$", line)
        if match:
            current_id = int(match.group(1))
            answers[current_id] = match.group(2).strip()
        elif re.fullmatch(r"\d{1,3}", line):
            current_id = int(line)
            answers[current_id] = pending_prefix
            pending_prefix = ""
        elif re.fullmatch(r"\d{1,3}", next_line):
            pending_prefix = line
        elif current_id is not None:
            answers[current_id] = clean_text(f"{answers[current_id]} {line}")
    return answers


def apply_source_answers(questions: list[dict], answers: dict[int, str], source: str) -> None:
    for question in questions:
        source_id = question["sourceQuestionId"]
        answer = answers.get(source_id)
        question["source"] = source
        question["answerStatus"] = "source-verified" if answer else "missing"
        question["answerText"] = answer or ""
        if not answer:
            continue
        needle = comparable(answer)
        scores = []
        for option in question["options"]:
            option_value = comparable(option)
            score = difflib.SequenceMatcher(None, needle, option_value).ratio()
            if option_value and option_value in needle:
                score = 1.0
            scores.append(score)
        best_index = max(range(len(scores)), key=scores.__getitem__)
        question["correctIndex"] = best_index
        question["answerMatchScore"] = round(scores[best_index], 3)


def parse_eccouncil(pdf: Path) -> list[dict]:
    lines: list[str] = []
    document = pymupdf.open(pdf)
    for page in document[1:]:
        for raw_line in page.get_text(sort=True).splitlines():
            line = raw_line.strip()
            if not line:
                lines.append("")
                continue
            if re.fullmatch(r"ECCouncil - 312-50v13", line):
                continue
            if re.fullmatch(r"\d+ of 411", line):
                continue
            if "店铺" in line:
                continue
            lines.append(line)
    text = "\n".join(lines)
    markers = list(
        re.finditer(
            r"(?m)^Question #:(\d+)(?:\s*-\s*\[([^\]]+)\])?\s*$",
            text,
        )
    )
    results: list[dict] = []
    option_re = re.compile(r"^\s*([A-D])\.\s+(.*)$")
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        chunk = text[marker.end() : end]
        source_id = int(marker.group(1))
        category = clean_text(marker.group(2) or "")
        if not category:
            category_match = re.match(r"\s*\[([^\]]+)\]\s*", chunk)
            if category_match:
                category = clean_text(category_match.group(1))
                chunk = chunk[category_match.end() :]
            else:
                category = "General CEH"
        answer_match = re.search(r"(?m)^Answer:\s*([A-D](?:\s+[A-E])*)\s*$", chunk)
        if not answer_match:
            raise ValueError(f"Missing answer in ECCouncil question {source_id}")
        before_answer = chunk[: answer_match.start()]
        after_answer = chunk[answer_match.end() :]
        answer_value = answer_match.group(1)
        malformed_explanation = re.search(r"(?m)^\s*E\.\s*([A-D])(.+)$", before_answer)
        if " " in answer_value and malformed_explanation:
            correct_letter = malformed_explanation.group(1)
            explanation = malformed_explanation.group(2) + before_answer[malformed_explanation.end() :]
            before_answer = before_answer[: malformed_explanation.start()]
        else:
            correct_letter = answer_value
            explanation_match = re.search(r"(?m)^Explanation\s*$", after_answer)
            explanation = (
                after_answer[explanation_match.end() :] if explanation_match else after_answer
            )

        question_lines: list[str] = []
        option_parts: dict[str, list[str]] = {}
        current_letter: str | None = None
        for raw_line in before_answer.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            option_match = option_re.match(raw_line)
            if option_match:
                current_letter = option_match.group(1)
                option_parts[current_letter] = [option_match.group(2)]
            elif current_letter is None:
                question_lines.append(line)
            else:
                option_parts[current_letter].append(line)

        options = [clean_text(" ".join(option_parts.get(letter, []))) for letter in LETTERS]
        while options and not options[-1]:
            options.pop()
        correct_index = LETTERS.index(correct_letter)
        results.append(
            {
                "sourceQuestionId": source_id,
                "question": clean_text(" ".join(question_lines)),
                "options": options,
                "correctIndex": correct_index,
                "answerText": options[correct_index] if len(options) == 4 else "",
                "answerStatus": "source-verified",
                "answerMatchScore": 1.0,
                "topic": category,
                "source": pdf.name,
                "explanationEn": clean_text(explanation),
            }
        )
    return results


def infer_topic(question: dict) -> str:
    text = f"{question['question']} {' '.join(question['options'])}".casefold()
    rules = [
        ("Cloud Computing", ("cloud", "aws", "azure", "s3", "docker", "container")),
        ("Web Application Hacking", ("sql injection", "xss", "web application", "http", "cookie", "session")),
        ("Wireless Network Hacking", ("wireless", "wifi", "wi-fi", "wpa", "bluetooth")),
        ("Cryptography", ("cipher", "encryption", "cryptograph", "hash", "rsa", "certificate")),
        ("Mobile Platform, IoT, and OT Hacking", ("android", "iphone", "mobile", "iot", "modbus", "scada")),
        ("Social Engineering", ("phishing", "social engineering", "tailgating", "shoulder surfing")),
        ("Malware Threats", ("malware", "trojan", "virus", "ransomware", "rootkit")),
        ("Network and Perimeter Hacking", ("network", "nmap", "firewall", "packet", "tcp", "udp", "icmp", "dns")),
        ("Reconnaissance Techniques", ("reconnaissance", "footprint", "osint", "google dork")),
    ]
    for topic, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return topic
    return "General CEH"


def validate_source(name: str, questions: list[dict], expected: int) -> None:
    if len(questions) != expected:
        raise ValueError(f"{name}: expected {expected} questions, parsed {len(questions)}")
    ids = [question["sourceQuestionId"] for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name}: duplicate question IDs")
    for question in questions:
        if (
            not question["question"]
            or not 2 <= len(question["options"]) <= 4
            or not all(question["options"])
        ):
            raise ValueError(
                f"{name} question {question['sourceQuestionId']}: malformed question/options"
            )


def main() -> None:
    first = parse_bulleted_questions(
        QUESTION_DIR / "ceh13-01.pdf", end_page=54, bullet_pattern="☐"
    )
    apply_source_answers(
        first,
        parse_answer_table(QUESTION_DIR / "ceh13-01.pdf", start_page=54),
        "ceh13-01.pdf",
    )

    second = parse_bulleted_questions(
        QUESTION_DIR / "ceh13-02.pdf", end_page=59, bullet_pattern="\uf0b7"
    )
    apply_source_answers(
        second,
        parse_answer_table(QUESTION_DIR / "ceh13-02.pdf", start_page=59),
        "ceh13-02.pdf",
    )

    third = parse_labeled_questions(QUESTION_DIR / "ceh13-03.pdf")
    for question in third:
        question.update(
            {
                "source": "ceh13-03.pdf",
                "answerStatus": "missing",
                "answerText": "",
            }
        )

    large = parse_eccouncil(QUESTION_DIR / "ECCouncil-312-50v13-2026.pdf")

    validate_source("ceh13-01.pdf", first, 125)
    validate_source("ceh13-02.pdf", second, 124)
    validate_source("ceh13-03.pdf", third, 125)
    validate_source("ECCouncil-312-50v13-2026.pdf", large, 542)

    all_questions = first + second + third + large
    for global_id, question in enumerate(all_questions, 1):
        question["id"] = global_id
        question.setdefault("topic", infer_topic(question))
        question.setdefault("explanationEn", "")
        question.setdefault("questionZh", "")
        question.setdefault("optionsZh", [])
        question.setdefault("explanation", "")

    OUTPUT.write_text(
        json.dumps(all_questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT.relative_to(ROOT)),
                "total": len(all_questions),
                "bySource": {
                    "ceh13-01.pdf": len(first),
                    "ceh13-02.pdf": len(second),
                    "ceh13-03.pdf": len(third),
                    "ECCouncil-312-50v13-2026.pdf": len(large),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
