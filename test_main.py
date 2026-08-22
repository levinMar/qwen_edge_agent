"""
test_main.py — Standard library unit test suite for main.py (FastAPI Edge Wrapper).
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from diagnostics_pb2 import DiagnosticData, IssueType, Severity, Status
from main import app, build_edge_command


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

    def test_build_edge_command_healthy(self):
        """Verify build_edge_command logic for a healthy leaf."""
        diag = DiagnosticData(
            issue_type=IssueType.OTHER,
            severity=Severity.NONE,
            confidence=0.95,
            raw_description="Healthy green leaf with no defects.",
        )
        cmd = build_edge_command(diag, source_node_id="test-node")

        self.assertEqual(cmd.source_node_id, "test-node")
        self.assertEqual(cmd.status, Status.HEALTHY)
        self.assertFalse(cmd.field_action.trigger_actuator)
        self.assertFalse(cmd.field_action.isolation_required)
        self.assertEqual(cmd.field_action.dosage_ml_per_sqm, 0.0)

    def test_build_edge_command_contagious_anomaly(self):
        """Verify build_edge_command logic for high-severity fungal infection."""
        diag = DiagnosticData(
            issue_type=IssueType.FUNGAL_INFECTION,
            severity=Severity.HIGH,
            confidence=0.88,
            raw_description="Severe fungal spotting covering 60% of leaf.",
        )
        cmd = build_edge_command(diag, source_node_id="test-node")

        self.assertEqual(cmd.status, Status.ANOMALY_DETECTED)
        self.assertTrue(cmd.field_action.trigger_actuator)
        self.assertTrue(cmd.field_action.isolation_required)
        self.assertEqual(cmd.field_action.dosage_ml_per_sqm, 15.0)

    def test_build_edge_command_non_contagious_anomaly(self):
        """Verify build_edge_command logic for nutrient deficiency."""
        diag = DiagnosticData(
            issue_type=IssueType.NUTRIENT_DEFICIENCY,
            severity=Severity.MEDIUM,
            confidence=0.75,
            raw_description="Chlorosis observed along outer leaf margins.",
        )
        cmd = build_edge_command(diag, source_node_id="test-node")

        self.assertEqual(cmd.status, Status.ANOMALY_DETECTED)
        self.assertTrue(cmd.field_action.trigger_actuator)
        self.assertFalse(cmd.field_action.isolation_required)
        self.assertEqual(cmd.field_action.dosage_ml_per_sqm, 10.0)

    @patch("main.constrained_diagnose")
    def test_diagnose_endpoint_constrained(self, mock_constrained):
        """Test POST /diagnose with constrained strategy."""
        mock_constrained.return_value = DiagnosticData(
            issue_type=IssueType.BLIGHT,
            severity=Severity.HIGH,
            confidence=0.92,
            raw_description="Blight lesions present.",
        )

        response = self.client.post(
            "/diagnose?strategy=constrained",
            data={"image_path": "./test_images/IMG_20241115_152228_HDR.jpg"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["source_node_id"], "edge-node-01")
        self.assertEqual(data["status"], "ANOMALY_DETECTED")
        self.assertEqual(data["diagnostic"]["issue_type"], "BLIGHT")
        self.assertEqual(data["diagnostic"]["severity"], "HIGH")
        self.assertTrue(data["field_action"]["trigger_actuator"])
        self.assertTrue(data["field_action"]["isolation_required"])

    @patch("main.freeform_diagnose")
    @patch("main.constrained_diagnose")
    def test_compare_endpoint(self, mock_constrained, mock_freeform):
        """Test POST /compare endpoint agreement reporting."""
        mock_constrained.return_value = DiagnosticData(
            issue_type=IssueType.PEST_INFESTATION,
            severity=Severity.MEDIUM,
            confidence=0.85,
            raw_description="Pest damage on leaf.",
        )
        mock_freeform.return_value = DiagnosticData(
            issue_type=IssueType.PEST_INFESTATION,
            severity=Severity.MEDIUM,
            confidence=0.50,
            raw_description="Observed aphids on underside.",
        )

        response = self.client.post(
            "/compare",
            data={"image_path": "./test_images/IMG_20241115_152228_HDR.jpg"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["agreement"])
        self.assertEqual(
            data["constrained"]["diagnostic"]["issue_type"], "PEST_INFESTATION"
        )
        self.assertEqual(
            data["freeform"]["diagnostic"]["issue_type"], "PEST_INFESTATION"
        )


if __name__ == "__main__":
    unittest.main()
