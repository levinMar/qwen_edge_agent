"""
Hardware Actuation Rules Engine
Translates Qwen AI Diagnostic findings (IssueType + Severity) into concrete hardware actuation directives for spraying bots and farm rovers.
"""
import diagnostics_pb2

# Rule-based mapping for issue types to target treatment chemicals & spray nozzle parameters
ACTUATION_RULES = {
    diagnostics_pb2.BLIGHT: {
        "chemical": "Fungicide_CopperMax",
        "dosage_base": 20.0,
        "isolation": True,
        "nozzle": diagnostics_pb2.HIGH_PRESSURE,
    },
    diagnostics_pb2.FUNGAL_INFECTION: {
        "chemical": "BioFungicide_Sulfur",
        "dosage_base": 15.0,
        "isolation": True,
        "nozzle": diagnostics_pb2.HIGH_PRESSURE,
    },
    diagnostics_pb2.PEST_INFESTATION: {
        "chemical": "Neem_Organic_Insecticide",
        "dosage_base": 25.0,
        "isolation": True,
        "nozzle": diagnostics_pb2.MEDIUM_SPRAY,
    },
    diagnostics_pb2.NUTRIENT_DEFICIENCY: {
        "chemical": "Liquid_Foliar_NPK_10-10-10",
        "dosage_base": 10.0,
        "isolation": False,
        "nozzle": diagnostics_pb2.MIST,
    },
    diagnostics_pb2.WATER_STRESS: {
        "chemical": "HydroMist_Wetting_Agent",
        "dosage_base": 30.0,
        "isolation": False,
        "nozzle": diagnostics_pb2.MIST,
    },
    diagnostics_pb2.VIRAL_INFECTION: {
        "chemical": "Antiviral_BioMist_Quarantine",
        "dosage_base": 0.0,
        "isolation": True,
        "nozzle": diagnostics_pb2.NOZZLE_OFF,
    },
}

SEVERITY_MULTIPLIER = {
    diagnostics_pb2.NONE: 0.0,
    diagnostics_pb2.LOW: 0.5,
    diagnostics_pb2.MEDIUM: 1.0,
    diagnostics_pb2.HIGH: 1.5,
}


def determine_field_action(
    issue_type: int,
    severity: int,
    actuator_id: str = "sprayer-bot-01",
) -> diagnostics_pb2.FieldAction:
    """
    Evaluates diagnostic findings against the rules engine to compute physical hardware actuation commands.
    """
    if issue_type == diagnostics_pb2.ISSUE_UNKNOWN or severity == diagnostics_pb2.NONE:
        return diagnostics_pb2.FieldAction(
            trigger_actuator=False,
            actuator_id=actuator_id,
            treatment_chemical="NONE",
            dosage_ml_per_sqm=0.0,
            isolation_required=False,
            nozzle_setting=diagnostics_pb2.NOZZLE_OFF,
        )

    rule = ACTUATION_RULES.get(
        issue_type,
        {
            "chemical": "General_Crop_Protectant",
            "dosage_base": 10.0,
            "isolation": False,
            "nozzle": diagnostics_pb2.MEDIUM_SPRAY,
        },
    )

    multiplier = SEVERITY_MULTIPLIER.get(severity, 1.0)
    calculated_dosage = rule["dosage_base"] * multiplier

    return diagnostics_pb2.FieldAction(
        trigger_actuator=True,
        actuator_id=actuator_id,
        treatment_chemical=rule["chemical"],
        dosage_ml_per_sqm=round(calculated_dosage, 2),
        isolation_required=rule["isolation"],
        nozzle_setting=rule["nozzle"],
    )
