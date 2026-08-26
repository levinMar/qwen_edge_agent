"""
test_main.py — Standard library unit test suite for main.py (FastAPI Edge Wrapper) & hardware dispatcher.
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

import diagnostics_pb2
from diagnostics_pb2 import DiagnosticData, IssueType, Severity, Status
from main import app, build_edge_command
from actuator_rules import determine_field_action


class TestMainApi(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        """Verify GET /health returns online status and metadata."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["node_id"], "edge-node-01")
        self.assertIn("timestamp", data)

    def test_actuator_rules_engine(self):
        """Verify rules engine maps IssueType + Severity to chemical & dosage."""
        action = determine_field_action(IssueType.BLIGHT, Severity.HIGH)
        self.assertTrue(action.trigger_actuator)
        self.assertEqual(action.treatment_chemical, "Fungicide_CopperMax")
        self.assertEqual(action.dosage_ml_per_sqm, 30.0)
        self.assertTrue(action.isolation_required)
        self.assertEqual(action.nozzle_setting, diagnostics_pb2.HIGH_PRESSURE)

    def test_build_edge_command_with_location(self):
        """Verify build_edge_command attaches GPS/zone location metadata."""
        diag = DiagnosticData(
            issue_type=IssueType.FUNGAL_INFECTION,
            severity=Severity.MEDIUM,
            confidence=0.88,
            raw_description="Fungal spots present.",
        )
        cmd = build_edge_command(
            diag,
            source_node_id="scout-node-01",
            latitude=-1.286,
            longitude=36.817,
            zone_id="ZONE-C2",
            row_id=8,
        )

        self.assertEqual(cmd.status, Status.ANOMALY_DETECTED)
        self.assertEqual(cmd.location.zone_id, "ZONE-C2")
        self.assertEqual(cmd.location.row_id, 8)
        self.assertAlmostEqual(cmd.location.latitude, -1.286)
        self.assertEqual(cmd.field_action.treatment_chemical, "BioFungicide_Sulfur")
        self.assertEqual(cmd.field_action.dosage_ml_per_sqm, 15.0)

    @patch("main.constrained_diagnose")
    def test_dispatch_endpoint(self, mock_constrained):
        """Test POST /dispatch endpoint hardware execution flow."""
        mock_constrained.return_value = DiagnosticData(
            issue_type=IssueType.BLIGHT,
            severity=Severity.HIGH,
            confidence=0.95,
            raw_description="Severe blight detected.",
        )

        response = self.client.post(
            "/dispatch",
            data={
                "image_path": "./test_images/IMG_20241115_152228_HDR.jpg",
                "latitude": -1.286389,
                "longitude": 36.817223,
                "zone_id": "ZONE-B4",
                "row_id": 12,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("edge_command", data)
        self.assertIn("hardware_execution", data)

        cmd = data["edge_command"]
        exec_info = data["hardware_execution"]

        self.assertEqual(cmd["location"]["zone_id"], "ZONE-B4")
        self.assertEqual(exec_info["status"], "ACTUATION_SUCCESS")
        self.assertEqual(exec_info["applied_chemical"], "Fungicide_CopperMax")
        self.assertEqual(exec_info["executed_dosage_ml"], 30.0)


if __name__ == "__main__":
    unittest.main()
