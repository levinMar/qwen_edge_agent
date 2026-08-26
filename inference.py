"""
inference.py — Qwen3.8-Max diagnostic inference module.

Provides constrained-taxonomy classification against the DiagnosticData
protobuf schema. The model is prompted to select directly from the fixed
IssueType enum names and return strict JSON, giving clean, parse-safe output
with no post-hoc mapping needed.

Returns a populated DiagnosticData protobuf message.
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


def _call_qwen(image_path: str, prompt: str, max_retries: int = 3) -> str:
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
    Constrained taxonomy classification.
    Prompts Qwen3.8-Max to select directly from the fixed IssueType enum
    and return strict JSON. Parsing is a straight lookup with no keyword
    mapping, giving clean, deterministic output suitable for hardware actuation.
    """
    prompt = f"""Examine this crop leaf image for signs of disease, pest damage and infestation,
or stress. Respond with ONLY a JSON object, no other text, in this exact form:

{{
  "issue_type": "<one of: {', '.join(ISSUE_TYPE_NAMES)}>",
  "severity": "<one of: {', '.join(SEVERITY_NAMES)}>",
  "confidence": <float 0.0-1.0>,
  "description": "<one sentence explaining what you observed>"
}}

If you see no issue, use issue_type "OTHER" is wrong for a healthy leaf —
in that case use severity "NONE" and describe the leaf as healthy."""

    raw = _call_qwen(image_path, prompt)

    # Strip markdown code fences if the model wraps the JSON
    stripped = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\n?```$", "", stripped.strip())

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {raw!r}") from e

    diagnostic = DiagnosticData()
    diagnostic.issue_type = IssueType.Value(parsed["issue_type"])
    diagnostic.severity = Severity.Value(parsed["severity"])
    diagnostic.confidence = float(parsed["confidence"])
    diagnostic.raw_description = parsed["description"]
    return diagnostic