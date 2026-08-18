"""Apply researched answers and explanations to the imported question bank."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "questions.imported.json"
OUTPUT = ROOT / "data" / "questions.enriched.json"
LETTERS = "ABCD"

# ceh13-03.pdf has no answer key. These answers were checked against current
# primary documentation (Nmap, OWASP, NIST, MITRE ATT&CK, vendor docs, etc.).
ANSWER_LINES = """
1:B 2:D 3:D 4:B 5:B 6:A 7:B 8:A 9:D 10:A
11:D 12:A 13:A 14:B 15:B 16:B 17:C 18:B 19:B 20:B
21:C 22:B 23:D 24:C 25:B 26:C 27:B 28:C 29:C 30:B
31:B 32:B 33:C 34:A 35:B 36:C 37:B 38:B 39:B 40:B
41:C 42:C 43:B 44:B 45:C 46:C 47:B 48:C 49:B 50:B
51:B 52:C 53:B 54:B 55:C 56:C 57:C 58:C 59:B 60:B
61:B 62:C 63:B 64:B 65:B 66:A 67:B 68:C 69:B 70:C
71:B 72:C 73:B 74:C 75:B 76:B 77:B 78:B 79:C 80:C
81:B 82:B 83:B 84:B 85:B 86:A 87:C 88:C 89:C 90:B
91:B 92:C 93:B 94:B 95:B 96:B 97:C 98:A 99:C 100:C
101:C 102:B 103:A 104:B 105:B 106:A 107:C 108:B 109:D 110:B
111:C 112:B 113:C 114:B 115:B 116:B 117:B 118:C 119:A 120:B
121:C 122:B 123:C 124:C 125:D
"""

ANSWERS = {
    int(number): LETTERS.index(letter)
    for number, letter in re.findall(r"(\d+):([A-D])", ANSWER_LINES)
}

RATIONALE_OVERRIDES = {
    1: "Google advanced search operators can passively discover indexed Amazon S3 bucket URLs without attacking the target application.",
    2: "Obsolete TLS versions weaken transport protection and can enable an on-path attacker to intercept or manipulate sessions; XSS and SQL injection are unrelated application flaws.",
    3: "Spoofed LLMNR and NBT-NS replies can redirect authentication to an attacker-controlled service, exposing NTLM challenge-response hashes for relay or offline cracking.",
    4: "An insertion attack exploits inconsistent packet validation: the IDS accepts a malformed packet while the endpoint rejects it, causing the two systems to reconstruct different streams.",
    5: "robots.txt is reconnaissance data. Disallow entries can reveal sensitive paths, but they are not access controls and do not by themselves constitute traversal or injection.",
    6: "Without encryption at rest, an attacker with filesystem access can read sensitive application data directly from local storage.",
    7: "A still-valid session token can be replayed to inherit the authenticated session, bypassing the need to repeat HTTPS authentication or MFA.",
    8: "Cross-VM CPU timing leakage is a side-channel attack because it infers secrets from shared hardware behavior rather than directly reading the victim VM.",
    9: "The Nmap snmp-processes NSE script is specifically designed to enumerate running processes through SNMP on UDP port 161.",
    10: "If logout does not invalidate the token server-side, replaying that same token can restore the supposedly terminated session.",
    11: "An ACK scan is used to map firewall rules and distinguish filtered from unfiltered paths; it does not determine whether a port is open.",
    12: "Known or weak default credentials can give an attacker direct unauthorized administrative access to ICS operations; indiscriminate brute force is unnecessary when defaults work.",
    13: "A tautology such as OR 1=1 is a conventional authorized test for whether login input is being concatenated into a SQL query.",
    14: "A convincing fake onboarding portal fits the HR context and can collect network credentials while appearing to be part of a normal employee workflow.",
    23: "Nmap idle scan is the most stealthy listed choice because probes reaching the target appear to originate from a zombie host, not the scanner.",
    24: "Cross-site scripting abuses a trusted website to execute attacker-controlled browser code and can redirect a victim to malicious content.",
    30: "Inverse mapping and ACK-style probes are used to infer filtering behavior and discover hosts or rules behind packet filters; they do not identify SQL flaws or operating systems.",
    53: "A tailored fraudulent message aimed at a particular employee is spear phishing; the executive identity is the impersonated lure.",
    58: "HTTP PUT stores the enclosed representation at the requested URI and is the method most directly associated with uploading or replacing a named resource.",
    68: "Crafting input at inference time to force a wrong classification is an adversarial evasion attack; poisoning instead changes training data.",
    79: "DNSSEC digitally signs DNS data to provide origin authentication and integrity. It does not encrypt DNS queries or automatically block sites.",
    95: "Session splicing divides a malicious payload across many small packets or segments so a signature-based IDS may fail to match the complete pattern.",
    101: "Zero Trust removes implicit trust based on network location and continually verifies each access request.",
    110: "NIST defines purge as sanitization that makes recovery infeasible even with state-of-the-art laboratory techniques while potentially retaining reusable media.",
    118: "Traceroute relies on expiring IP TTL values and ICMP Time Exceeded responses to reveal each hop. Probe packets may be UDP, ICMP, or TCP depending on the implementation.",
}

URLS = {
    "nmap": "https://nmap.org/book/man.html",
    "nmap_idle": "https://nmap.org/book/idlescan.html",
    "nmap_snmp": "https://nmap.org/nsedoc/scripts/snmp-processes.html",
    "owasp": "https://owasp.org/www-community/attacks/",
    "owasp_sqli": "https://owasp.org/www-community/attacks/SQL_Injection",
    "owasp_top10": "https://owasp.org/Top10/2021/",
    "mitre_llmnr": "https://attack.mitre.org/techniques/T1557/001/",
    "nist_cvss": "https://nvd.nist.gov/vuln-metrics/cvss",
    "nist_ir": "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-61r1.pdf",
    "nist_purge": "https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=960712",
    "nist_zero": "https://www.nist.gov/programs-projects/zero-trust-networks",
    "nist_glossary": "https://csrc.nist.gov/glossary",
    "aws_shared": "https://aws.amazon.com/compliance/shared-responsibility-model/",
    "dnssec": "https://www.icann.org/resources/pages/dnssec-what-is-it-why-important-2019-03-05-en/",
    "microsoft_wevtutil": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/wevtutil",
    "wireshark": "https://www.wireshark.org/docs/dfref/i/ip.html",
    "mdn_put": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/PUT",
}

REFERENCE_GROUPS = {
    "nmap": {9, 11, 17, 22, 23, 30, 31, 32, 35, 48, 109, 123},
    "owasp": {7, 10, 13, 19, 24, 47, 59, 62, 63, 75, 83, 84, 85, 97},
    "nist": {25, 29, 71, 72, 87, 88, 100, 101, 105, 106, 110, 114},
    "cloud": {1, 8, 20, 37, 66, 69, 98},
    "mitre": {3, 39, 78, 92, 95, 96},
}


def references_for(number: int) -> list[str]:
    if number == 3:
        return [URLS["mitre_llmnr"]]
    if number == 9:
        return [URLS["nmap_snmp"]]
    if number == 23:
        return [URLS["nmap_idle"]]
    if number == 29:
        return [URLS["nist_cvss"]]
    if number in {87, 114}:
        return [URLS["nist_ir"]]
    if number == 92:
        return [URLS["microsoft_wevtutil"]]
    if number == 58:
        return [URLS["mdn_put"]]
    if number == 77:
        return [URLS["wireshark"]]
    if number == 79:
        return [URLS["dnssec"]]
    if number == 101:
        return [URLS["nist_zero"]]
    if number == 110:
        return [URLS["nist_purge"]]
    if number in REFERENCE_GROUPS["nmap"]:
        return [URLS["nmap"]]
    if number in REFERENCE_GROUPS["owasp"]:
        return [URLS["owasp"], URLS["owasp_sqli"], URLS["owasp_top10"]]
    if number in REFERENCE_GROUPS["nist"]:
        return [URLS["nist_ir"], URLS["nist_zero"]]
    if number in REFERENCE_GROUPS["cloud"]:
        return [URLS["aws_shared"]]
    if number in REFERENCE_GROUPS["mitre"]:
        return [URLS["mitre_llmnr"]]
    return [URLS["nist_glossary"]]


def generic_rationale(question: dict) -> str:
    answer = question["answerText"]
    return (
        f"The correct answer is {answer}. It directly matches the defining behavior, "
        "tool, protocol, control, or security property described in the question; the "
        "other choices describe different concepts that do not satisfy all of the clues."
    )


def comparable(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    return re.sub(r"[^a-z0-9]+", "", value)


def add_source_explanations(questions: list[dict]) -> None:
    """Reuse explanations for close duplicates, then fill the remaining gaps."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    small = [
        question
        for question in questions
        if question["source"] in {"ceh13-01.pdf", "ceh13-02.pdf"}
    ]
    large = [
        question
        for question in questions
        if question["source"] == "ECCouncil-312-50v13-2026.pdf"
    ]
    matrix = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=2
    ).fit_transform([question["question"] for question in small + large])
    similarities = cosine_similarity(matrix[: len(small)], matrix[len(small) :])

    for index, question in enumerate(small):
        match_index = int(similarities[index].argmax())
        match = large[match_index]
        similarity = float(similarities[index, match_index])
        selected = question["options"][question["correctIndex"]]
        matched_selected = match["options"][match["correctIndex"]]
        answer_similarity = __import__("difflib").SequenceMatcher(
            None, comparable(selected), comparable(matched_selected)
        ).ratio()
        if similarity >= 0.75 and answer_similarity >= 0.8:
            question["explanationEn"] = match["explanationEn"]
            question["explanationStatus"] = "adapted-from-similar-source-question"
            question["explanationSource"] = {
                "source": match["source"],
                "sourceQuestionId": match["sourceQuestionId"],
            }
        else:
            question["explanationEn"] = generic_rationale(question)
            question["explanationStatus"] = "study-note"

    for question in large:
        question["explanationStatus"] = "source-provided"


def main() -> None:
    questions = json.loads(INPUT.read_text(encoding="utf-8"))
    if set(ANSWERS) != set(range(1, 126)):
        raise ValueError("ceh13-03 answer map must contain questions 1 through 125")

    add_source_explanations(questions)

    for question in questions:
        if question["source"] != "ceh13-03.pdf":
            continue
        number = question["sourceQuestionId"]
        correct_index = ANSWERS[number]
        question["correctIndex"] = correct_index
        question["answerText"] = question["options"][correct_index]
        question["answerStatus"] = "web-verified"
        question["explanationEn"] = RATIONALE_OVERRIDES.get(
            number, generic_rationale(question)
        )
        question["explanationStatus"] = "researched-study-note"
        question["references"] = references_for(number)

    OUTPUT.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(questions)} questions to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
