"""
inference.py — Qwen3.8-Max diagnostic inference module.

Provides two classification strategies against the same DiagnosticData
schema, for comparison:

  1. constrained_diagnose()  — prompts Qwen3.8-Max to select directly from
     the IssueType enum names (tight coupling, cleaner output)
  2. freeform_diagnose()     — prompts Qwen3.8-Max for a natural description,
     then maps it onto IssueType via keyword matching (looser coupling,
     more robust to prompt/model drift, preserves raw model language)

Both return a populated DiagnosticData protobuf message.
"""

import os
import re
import json
import time
import dashscope
from dashscope import MultiModalConversation
from dotenv import load_dotenv

from diagnostics_pb2 import DiagnosticData, IssueType, Severity

load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

MODEL_NAME = "qwen3.8-max"

# Human-readable names for the constrained prompt — must match the enum
# exactly so the model's text output maps back cleanly.
ISSUE_TYPE_NAMES = [
    "BLIGHT",
    "PEST_INFESTATION",
    "NUTRIENT_DEFICIENCY",
    "FUNGAL_INFECTION",
    "VIRAL_INFECTION",
    "WATER_STRESS",
    "OTHER",
]

SEVERITY_NAMES = ["NONE", "LOW", "MEDIUM", "HIGH"]

# Keyword fallback map for the free-form path.
ISSUE_KEYWORDS = {
    IssueType.BLIGHT: ["blight"],
    IssueType.PEST_INFESTATION: ["pest", "insect", "aphid", "larvae", "infestation"],
    IssueType.NUTRIENT_DEFICIENCY: ["deficiency", "yellowing", "chlorosis", "nutrient"],
    IssueType.FUNGAL_INFECTION: ["fungal", "mold", "mildew", "fungus"],
    IssueType.VIRAL_INFECTION: ["viral", "mosaic virus", "virus"],
    IssueType.WATER_STRESS: ["wilting", "drought", "overwatered", "water stress"],
}

# Matches "85%", "85 %", "0.85", ".85" — used by freeform confidence extraction.
_CONFIDENCE_PATTERN = re.compile(r'\b(\d{1,3})\s*%|(?<!\d)(0?\.\d+)(?!\d)')


def _call_qwen_vl(image_path: str, prompt: str, max_retries: int = 3) -> str:
    """Send an image + text prompt to Qwen3.8-Max, return the raw text response.

    Retries on transient network/API failures with exponential backoff
    (1 s, 2 s, 4 s). Raises RuntimeError if all attempts are exhausted.
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"image": image_path},
                {"text": prompt},
            ],
        }
    ]

    last_error = None
    for attempt in range(max_retries):
        try:
            response = MultiModalConversation.call(model=MODEL_NAME, messages=messages)
            if response.status_code != 200:
                raise RuntimeError(
                    f"DashScope call failed: {response.code} — {response.message}"
                )
            return response.output.choices[0].message.content[0]["text"]
        except Exception as e:
            last_error = e
            wait = 2 ** attempt
            print(
                f"  [retry {attempt + 1}/{max_retries}] "
                f"{type(e).__name__}: {e} — waiting {wait}s"
            )
            time.sleep(wait)

    raise RuntimeError(f"Failed after {max_retries} attempts. Last error: {last_error}")


def constrained_diagnose(image_path: str) -> DiagnosticData:
    """
    Strategy 1: prompt-level constraint.
    Ask the model to choose directly from the fixed taxonomy and return
    strict JSON, so parsing is a straight lookup rather than a mapping.
    """
    prompt = f"""Examine this crop leaf image for signs of disease, pest damage,
or stress. Respond with ONLY a JSON object, no other text, in this exact form:

{{
  "issue_type": "<one of: {', '.join(ISSUE_TYPE_NAMES)}>",
  "severity": "<one of: {', '.join(SEVERITY_NAMES)}>",
  "confidence": <float 0.0-1.0>,
  "description": "<one sentence explaining what you observed>"
}}

If you see no issue, use issue_type "OTHER" is wrong for a healthy leaf —
in that case use severity "NONE" and describe the leaf as healthy."""

    raw = _call_qwen_vl(image_path, prompt)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {raw!r}") from e

    diagnostic = DiagnosticData()
    diagnostic.issue_type = IssueType.Value(parsed["issue_type"])
    diagnostic.severity = Severity.Value(parsed["severity"])
    diagnostic.confidence = float(parsed["confidence"])
    diagnostic.raw_description = parsed["description"]
    return diagnostic


def classify_issue(raw_text: str) -> IssueType:
    """Map free-form model text onto the closed IssueType taxonomy."""
    text = raw_text.lower()
    for issue_type, keywords in ISSUE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return issue_type
    return IssueType.OTHER if raw_text.strip() else IssueType.ISSUE_UNKNOWN


def _extract_confidence(raw_text: str) -> float:
    """Extract a confidence value from free-form text.

    Accepts "85%", "85 %", "0.85", or ".85". Returns 0.5 as fallback
    when no numeric confidence is found — preserving the original behaviour
    while making the fallback explicit and documented.
    """
    match = _CONFIDENCE_PATTERN.search(raw_text)
    if not match:
        return 0.5  # model gave no numeric estimate — explicit fallback

    percentage, decimal = match.group(1), match.group(2)
    if percentage is not None:
        return min(float(percentage) / 100.0, 1.0)
    return float(decimal)


def freeform_diagnose(image_path: str) -> DiagnosticData:
    """
    Strategy 2: free-form + post-hoc mapping.
    Let the model describe what it sees naturally, then classify the
    description ourselves. More robust to model phrasing drift; keeps
    the model's original language even when the mapping is uncertain.
    """
    prompt = """Examine this crop leaf image for signs of disease, pest damage,
or stress. Describe in one or two sentences what you observe, including
your best estimate of severity (none, low, medium, or high) and how
confident you are (as a percentage)."""

    raw = _call_qwen_vl(image_path, prompt)

    diagnostic = DiagnosticData()
    diagnostic.issue_type = classify_issue(raw)
    diagnostic.raw_description = raw
    diagnostic.confidence = _extract_confidence(raw)

    lowered = raw.lower()
    if "high" in lowered:
        diagnostic.severity = Severity.HIGH
    elif "medium" in lowered or "moderate" in lowered:
        diagnostic.severity = Severity.MEDIUM
    elif "low" in lowered or "mild" in lowered:
        diagnostic.severity = Severity.LOW
    else:
        diagnostic.severity = Severity.NONE

    return diagnostic