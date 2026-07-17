"""Tiny keyword-based MITRE ATT&CK mapper.

This is a deliberately small starter ruleset (source="rule" in
alert_mitre) so alert ingestion has *something* real to map against
before Phase 6 adds an AI-based mapper (source="ai") and Phase 5 adds a
proper detection-engineering ruleset. Confidence is a fixed heuristic,
not a computed score.
"""

KEYWORD_TECHNIQUES: list[tuple[str, str]] = [
    ("brute", "T1110"),
    ("password guess", "T1110.001"),
    ("powershell", "T1059.001"),
    ("phish", "T1566"),
    ("rdp", "T1021.001"),
    ("remote desktop", "T1021.001"),
    ("scheduled task", "T1053"),
    ("valid account", "T1078"),
    ("credential dump", "T1003"),
    ("privilege escalation", "T1068"),
    ("process injection", "T1055"),
    ("port scan", "T1046"),
    ("exfil", "T1041"),
    ("ransomware", "T1486"),
    ("encrypted for impact", "T1486"),
]

RULE_CONFIDENCE = 0.5


def match_techniques(*texts: str | None) -> list[str]:
    haystack = " ".join(t.lower() for t in texts if t)
    matched: list[str] = []
    for keyword, technique_id in KEYWORD_TECHNIQUES:
        if keyword in haystack and technique_id not in matched:
            matched.append(technique_id)
    return matched
