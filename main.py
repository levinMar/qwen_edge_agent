"""
main.py — FastAPI wrapper for the MiRIHI Qwen-VL Edge Diagnostic Agent.

Exposes edge inference endpoints over HTTP:
  - GET /health           — Health check and edge node metadata
  - POST /diagnose        — Run single strategy classification (constrained vs freeform)
  - POST /compare         — Run both strategies side-by-side and report agreement
  - POST /dispatch        — Full hardware dispatch: runs diagnosis, evaluates actuation rules,
                            packages location-aware EdgeCommand Protobuf, and dispatches to spraying bot.

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
    Location,
)
from inference import constrained_diagnose, freeform_diagnose
from actuator_rules import determine_field_action
from simulated_sprayer_bot import SimulatedSprayerBot

app = FastAPI(
    title="MiRIHI Qwen-VL Edge Diagnostic Agent",
    description="Edge crop diagnostic inference pipeline with protobuf command wrapping & hardware actuation dispatch.",
    version="0.1.0",
)

bot_simulator = SimulatedSprayerBot()


def build_edge_command(
    diagnostic: DiagnosticData,
    source_node_id: str = "edge-node-01",
    latitude: float = 0.0,
    longitude: float = 0.0,
    zone_id: str = "",
    row_id: int = 0,
) -> EdgeCommand:
    """
    Wraps DiagnosticData into a full EdgeCommand protobuf message, attaching location metadata
    and computing hardware actuation FieldAction using the actuator rules engine.
    """
    cmd = EdgeCommand()
    cmd.source_node_id = source_node_id
    cmd.timestamp_unix_ms = int(time.time() * 1000)

    # Attach location metadata
    cmd.location.latitude = latitude
    cmd.location.longitude = longitude
    cmd.location.zone_id = zone_id
    cmd.location.row_id = row_id

    cmd.diagnostic.CopyFrom(diagnostic)

    # Determine status & hardware action rules
    if (
        diagnostic.severity == Severity.NONE
        or diagnostic.issue_type == IssueType.ISSUE_UNKNOWN
    ):
        cmd.status = Status.HEALTHY
        field_action = determine_field_action(
            diagnostic.issue_type, Severity.NONE
        )
    else:
        cmd.status = Status.ANOMALY_DETECTED
        field_action = determine_field_action(
            diagnostic.issue_type, diagnostic.severity
        )

    cmd.field_action.CopyFrom(field_action)
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


@app.post("/dispatch")
async def dispatch_hardware_action(
    latitude: float = Form(0.0, description="Scout GPS latitude"),
    longitude: float = Form(0.0, description="Scout GPS longitude"),
    zone_id: str = Form("ZONE-A1", description="Farm zone identifier"),
    row_id: int = Form(1, description="Farm row number"),
    strategy: Literal["constrained", "freeform"] = Form("constrained"),
    file: Optional[UploadFile] = File(None),
    image_path: Optional[str] = Form(None),
):
    """
    Full Hardware Dispatch Workflow:
    1. Receives crop leaf image + farm location coordinates from scouting agrover.
    2. Runs Qwen AI diagnostic inference.
    3. Evaluates hardware actuation rules (chemical selection, dosage ml/m², nozzle pressure).
    4. Encodes location-aware EdgeCommand Protobuf message.
    5. Dispatches command to spraying bot hardware simulator.
    """
    target_path, is_temp = _resolve_image_file(file, image_path)

    try:
        if strategy == "constrained":
            diagnostic = constrained_diagnose(target_path)
        else:
            diagnostic = freeform_diagnose(target_path)

        edge_cmd = build_edge_command(
            diagnostic=diagnostic,
            source_node_id="scout-agrover-01",
            latitude=latitude,
            longitude=longitude,
            zone_id=zone_id,
            row_id=row_id,
        )

        # Dispatch command to spraying bot simulator
        bot_response = bot_simulator.execute_command(edge_cmd)

        return {
            "edge_command": MessageToDict(edge_cmd, preserving_proto_field_name=True),
            "hardware_execution": bot_response,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if is_temp and os.path.exists(target_path):
            os.remove(target_path)
