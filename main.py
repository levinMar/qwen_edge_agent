"""
main.py — FastAPI wrapper for the MiRIHI Qwen-VL Edge Diagnostic Agent.

Exposes edge inference endpoints over HTTP:
  - GET /health           — Health check and edge node metadata
  - POST /diagnose        — Run single strategy classification (constrained vs freeform)
  - POST /compare         — Run both strategies side-by-side and report agreement

Responses wrap diagnostic inference outputs in the top-level EdgeCommand
protobuf message (diagnostics.proto), returning serialized JSON.
"""

import os
import time
import tempfile
from typing import Optional, Literal
from fastapi import FastAPI, File, UploadFile, Form, Query, HTTPException
from google.protobuf.json_format import MessageToDict

from diagnostics_pb2 import (
    EdgeCommand,
    Status,
    Severity,
    IssueType,
    DiagnosticData,
    FieldAction,
)
from inference import constrained_diagnose, freeform_diagnose

app = FastAPI(
    title="MiRIHI Qwen-VL Edge Diagnostic Agent",
    description="Edge crop diagnostic inference pipeline with protobuf command wrapping.",
    version="0.1.0",
)


def build_edge_command(
    diagnostic: DiagnosticData, source_node_id: str = "edge-node-01"
) -> EdgeCommand:
    """
    Wraps DiagnosticData into a full EdgeCommand protobuf message, computing
    overall Status and actuation FieldAction rules.
    """
    cmd = EdgeCommand()
    cmd.source_node_id = source_node_id
    cmd.timestamp_unix_ms = int(time.time() * 1000)

    cmd.diagnostic.CopyFrom(diagnostic)

    # Determine status & actuator response logic
    if (
        diagnostic.severity == Severity.NONE
        or diagnostic.issue_type == IssueType.OTHER
        or diagnostic.issue_type == IssueType.ISSUE_UNKNOWN
    ):
        cmd.status = Status.HEALTHY
        cmd.field_action.trigger_actuator = False
        cmd.field_action.isolation_required = False
        cmd.field_action.dosage_ml_per_sqm = 0.0
    else:
        cmd.status = Status.ANOMALY_DETECTED
        cmd.field_action.trigger_actuator = True

        # Contagious issues require isolation if medium or high severity
        if (
            diagnostic.issue_type in (IssueType.BLIGHT, IssueType.FUNGAL_INFECTION)
            and diagnostic.severity in (Severity.MEDIUM, Severity.HIGH)
        ):
            cmd.field_action.isolation_required = True
        else:
            cmd.field_action.isolation_required = False

        # Dosage rule based on severity
        if diagnostic.severity == Severity.HIGH:
            cmd.field_action.dosage_ml_per_sqm = 15.0
        elif diagnostic.severity == Severity.MEDIUM:
            cmd.field_action.dosage_ml_per_sqm = 10.0
        else:
            cmd.field_action.dosage_ml_per_sqm = 5.0

    return cmd


def _resolve_image_file(
    file: Optional[UploadFile] = None, image_path: Optional[str] = None
) -> tuple[str, bool]:
    """
    Helper to resolve target image path from uploaded file or local path string.
    Returns (path, is_temporary_flag).
    """
    if file and file.filename:
        # Save upload to temporary file
        suffix = os.path.splitext(file.filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = file.file.read()
            tmp.write(content)
            tmp_path = tmp.name
        return tmp_path, True
    elif image_path:
        if not os.path.exists(image_path):
            raise HTTPException(
                status_code=404, detail=f"Image path not found: {image_path}"
            )
        return image_path, False
    else:
        raise HTTPException(
            status_code=400,
            detail="Either an image file upload or image_path parameter must be provided.",
        )


@app.get("/health")
def health_check():
    """Health check and node status metadata."""
    return {
        "status": "online",
        "service": "MiRIHI Qwen-VL Edge Diagnostic Agent",
        "node_id": "edge-node-01",
        "timestamp": int(time.time()),
    }


@app.post("/diagnose")
async def diagnose(
    strategy: Literal["constrained", "freeform"] = Query(
        "constrained", description="Classification strategy to use"
    ),
    file: Optional[UploadFile] = File(None),
    image_path: Optional[str] = Form(None),
):
    """
    Run diagnostic inference on a leaf image using the specified strategy.
    Returns serialized EdgeCommand protobuf.
    """
    target_path, is_temp = _resolve_image_file(file, image_path)

    try:
        if strategy == "constrained":
            diagnostic = constrained_diagnose(target_path)
        else:
            diagnostic = freeform_diagnose(target_path)

        edge_cmd = build_edge_command(diagnostic)
        return MessageToDict(edge_cmd, preserving_proto_field_name=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if is_temp and os.path.exists(target_path):
            os.remove(target_path)


@app.post("/compare")
async def compare_strategies(
    file: Optional[UploadFile] = File(None),
    image_path: Optional[str] = Form(None),
):
    """
    Run both constrained and freeform classification strategies side-by-side
    against the target leaf image and report agreement.
    """
    target_path, is_temp = _resolve_image_file(file, image_path)

    try:
        constrained_diag = constrained_diagnose(target_path)
        freeform_diag = freeform_diagnose(target_path)

        constrained_cmd = build_edge_command(constrained_diag)
        freeform_cmd = build_edge_command(freeform_diag)

        agree = constrained_diag.issue_type == freeform_diag.issue_type

        return {
            "agreement": agree,
            "constrained": MessageToDict(
                constrained_cmd, preserving_proto_field_name=True
            ),
            "freeform": MessageToDict(
                freeform_cmd, preserving_proto_field_name=True
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if is_temp and os.path.exists(target_path):
            os.remove(target_path)
