"""
Simulated Hardware Sprayer Bot
Receives location-aware EdgeCommand Protobuf messages, simulates GPS/zone navigation, and triggers physical pump relays.
"""
import time
import diagnostics_pb2
from google.protobuf.json_format import MessageToJson


class SimulatedSprayerBot:
    """
    Simulates a physical field sprayer bot (e.g., ESP32-S3 or ROS 2 agricultural rover).
    """

    def __init__(self, bot_id: str = "sprayer-bot-01"):
        self.bot_id = bot_id
        self.current_zone = "BASE_STATION"
        self.pump_active = False

    def execute_command(self, edge_command_proto: diagnostics_pb2.EdgeCommand) -> dict:
        """
        Processes a Protobuf EdgeCommand and executes physical navigation & spraying relay logic.
        """
        loc = edge_command_proto.location
        action = edge_command_proto.field_action
        diag = edge_command_proto.diagnostic

        # 1. Navigation Phase
        target_zone = loc.zone_id if loc.zone_id else f"GPS({loc.latitude:.4f}, {loc.longitude:.4f})"
        print(f"\n[ROBOT] [{self.bot_id}] RECEIVING COMMAND from node '{edge_command_proto.source_node_id}'...")
        print(f"[NAV] NAVIGATING to target location: Zone '{target_zone}', Row {loc.row_id} (Lat: {loc.latitude}, Lon: {loc.longitude})")
        self.current_zone = target_zone

        # 2. Actuation Decision
        if not action.trigger_actuator:
            print(f"[STANDBY] [{self.bot_id}] Target area is HEALTHY or NO ACTION REQUIRED. Standby.")
            return {
                "bot_id": self.bot_id,
                "status": "STANDBY",
                "current_zone": self.current_zone,
                "executed_dosage_ml": 0.0,
            }

        # 3. Hardware Relay Execution (Pump & Nozzle activation)
        nozzle_name = diagnostics_pb2.NozzleType.Name(action.nozzle_setting)
        issue_name = diagnostics_pb2.IssueType.Name(diag.issue_type)
        severity_name = diagnostics_pb2.Severity.Name(diag.severity)

        print(f"[ALERT] [{self.bot_id}] ANOMALY CONFIRMED: {issue_name} (Severity: {severity_name})")
        print(f"[RELAY] PUMP RELAY ON: Chemical = '{action.treatment_chemical}' | Dosage = {action.dosage_ml_per_sqm} ml/m² | Nozzle = {nozzle_name}")
        if action.isolation_required:
            print(f"[QUARANTINE] ISOLATION ALERT: Marking Zone '{self.current_zone}' for quarantine.")

        self.pump_active = True
        time.sleep(0.05)  # Simulate relay execution pulse
        self.pump_active = False

        print(f"[SUCCESS] [{self.bot_id}] ACTUATION COMPLETE. Returning to standby.\n")

        return {
            "bot_id": self.bot_id,
            "status": "ACTUATION_SUCCESS",
            "current_zone": self.current_zone,
            "applied_chemical": action.treatment_chemical,
            "executed_dosage_ml": action.dosage_ml_per_sqm,
            "nozzle_mode": nozzle_name,
            "isolation_active": action.isolation_required,
        }


if __name__ == "__main__":
    # Quick standalone test of the simulated sprayer bot
    cmd = diagnostics_pb2.EdgeCommand()
    cmd.source_node_id = "scout-agrover-01"
    cmd.timestamp_unix_ms = int(time.time() * 1000)
    cmd.status = diagnostics_pb2.ANOMALY_DETECTED

    cmd.location.latitude = -1.286389
    cmd.location.longitude = 36.817223
    cmd.location.zone_id = "ZONE-B4"
    cmd.location.row_id = 12

    cmd.diagnostic.issue_type = diagnostics_pb2.FUNGAL_INFECTION
    cmd.diagnostic.severity = diagnostics_pb2.HIGH
    cmd.diagnostic.confidence = 0.92
    cmd.diagnostic.raw_description = "High density fungal leaf spots."

    cmd.field_action.trigger_actuator = True
    cmd.field_action.actuator_id = "sprayer-bot-01"
    cmd.field_action.treatment_chemical = "BioFungicide_Sulfur"
    cmd.field_action.dosage_ml_per_sqm = 22.5
    cmd.field_action.isolation_required = True
    cmd.field_action.nozzle_setting = diagnostics_pb2.HIGH_PRESSURE

    bot = SimulatedSprayerBot()
    bot.execute_command(cmd)
