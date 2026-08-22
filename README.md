# MiRIHI Qwen Edge Diagnostic Agent

> Autonomous edge crop disease diagnostic microservice powered by **Qwen3.8-Max** with a dual-strategy classification pipeline, Protocol Buffer command wrapping, and hardware actuation mapping.

---

## 🌟 Overview & Purpose

**MiRIHI Qwen Edge Agent** is an edge intelligence microservice designed for autonomous agricultural rovers and field monitoring nodes. It analyzes crop leaf images captured by onboard cameras (e.g., ESP32-CAM nodes), runs multimodal AI diagnostics via **Qwen3.8-Max**, and packages diagnostic findings into structured **Protocol Buffer (`EdgeCommand`)** messages to trigger immediate physical field actions (such as automated spraying, isolation alerts, or routine logging).

---

## 🔬 Core Feature: Dual Classification Strategies

A primary architectural highlight of this system is its **Dual-Strategy Pipeline** implemented in [`inference.py`](file:///c:/Users/Administrator/Desktop/qwen_edge_agents/inference.py). It addresses a fundamental design tension in deploying LLMs/VLMs for real-time edge control: **tight structured coupling vs. raw model expressiveness**.

```
                           ┌───────────────────────────────┐
                           │      Crop Leaf Image          │
                           └───────────────┬───────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
       ┌─────────────────────────┐                   ┌─────────────────────────┐
       │   Strategy 1:           │                   │   Strategy 2:           │
       │   Constrained Prompt    │                   │   Unrestricted /        │
       │   (JSON Taxonomy)       │                   │   Free-Form Prompt      │
       └────────────┬────────────┘                   └────────────┬────────────┘
                    │                                             │
                    ▼                                             ▼
       Strict JSON Enum Output                       Natural Language Description
       "issue_type": "BLIGHT"                         "Yellow spots and fungal mold"
                    │                                             │
                    │                                             ▼
                    │                                Keyword Matching & Extraction
                    │                                issue_type: FUNGAL_INFECTION
                    │                                             │
                    └──────────────────────┬──────────────────────┘
                                           ▼
                               ┌───────────────────────┐
                               │    DiagnosticData     │
                               │   Protobuf Message    │
                               └───────────────────────┘
```

### Strategy 1: Constrained Taxonomy (`constrained_diagnose`)
* **How it works**: Prompts Qwen3.8-Max to select strictly from a pre-defined closed taxonomy of `IssueType` enum values (`BLIGHT`, `PEST_INFESTATION`, `NUTRIENT_DEFICIENCY`, `FUNGAL_INFECTION`, `VIRAL_INFECTION`, `WATER_STRESS`, `OTHER`) and return a raw JSON object.
* **Pros**: Zero post-processing needed, low latency, tight integration with downstream enum logic, zero mapping ambiguity.
* **Cons**: Risk of JSON parsing failures if the model hallucinates non-JSON syntax or unlisted keys.

### Strategy 2: Unrestricted / Free-Form (`freeform_diagnose`)
* **How it works**: Prompts Qwen3.8-Max for a natural, unconstrained visual description, estimated severity, and confidence percentage. Uses post-hoc keyword extraction and regex pattern matching to map the raw response back into the closed `IssueType` enum.
* **Pros**: Highly robust against model phrasing drift, preserves the raw, unedited model reasoning in `raw_description`, catches visual nuances that rigid enums miss.
* **Cons**: Requires heuristic post-processing (keyword maps, regex extraction) which can misclassify ambiguous descriptions.

---

### ⚔️ Performance & Output Comparison

| Metric / Aspect | Strategy 1: Constrained | Strategy 2: Unrestricted / Free-Form |
| :--- | :--- | :--- |
| **Output Format** | Rigid JSON (`{"issue_type": "BLIGHT", ...}`) | Natural Prose ("The leaf shows signs of fungal mold with high severity...") |
| **Downstream Parsing** | Direct JSON deserialization into Proto | Keyword matching + Regex extraction for confidence/severity |
| **Drift Resistance** | High dependency on strict JSON adherence | High resilience to model updates and natural language variations |
| **Context Preservation** | Summarized into single key-value strings | Full explanatory reasoning preserved in `raw_description` |
| **Real-world Use Case** | Fast automated actuation (e.g. spray triggers) | Detailed telemetry logging, human operator audit, fallback validation |

---

## 🛠️ Codebase Architecture

```
qwen_edge_agents/
├── diagnostics.proto     # Protobuf schema defining DiagnosticData, FieldAction, EdgeCommand
├── diagnostics_pb2.py    # Compiled Python Protocol Buffer bindings
├── inference.py          # Dual-strategy inference engine calling Qwen3.8-Max multimodal API
├── main.py               # FastAPI microservice wrapper providing /diagnose and /compare
├── compare.py            # Side-by-side strategy benchmark & agreement reporting script
├── test_main.py          # Unit test suite verifying FastAPI endpoints & command generation
└── test_images/          # Sample leaf dataset for edge testing
```

---

## 🚀 API Endpoints (`main.py`)

### 1. `GET /health`
Returns node status and system metadata.

### 2. `POST /diagnose`
Runs single-strategy inference on an uploaded image file or local image path.
* **Query Params**: `strategy=constrained` or `strategy=freeform`
* **Response**: Serialized `EdgeCommand` Protobuf JSON containing `DiagnosticData` and computed `FieldAction` (dosage, isolation requirements, actuator triggers).

### 3. `POST /compare`
Runs **both** strategies side-by-side against the same image and reports agreement.

**Example Response**:
```json
{
  "agreement": true,
  "constrained": {
    "source_node_id": "edge-node-01",
    "status": "ANOMALY_DETECTED",
    "diagnostic": {
      "issue_type": "FUNGAL_INFECTION",
      "severity": "HIGH",
      "confidence": 0.92,
      "raw_description": "Severe fungal leaf spot observed."
    },
    "field_action": {
      "trigger_actuator": true,
      "dosage_ml_per_sqm": 15.0,
      "isolation_required": true
    }
  },
  "freeform": {
    "source_node_id": "edge-node-01",
    "status": "ANOMALY_DETECTED",
    "diagnostic": {
      "issue_type": "FUNGAL_INFECTION",
      "severity": "HIGH",
      "confidence": 0.85,
      "raw_description": "The leaf exhibits dense white powdery mildew with high severity (~85% confidence)."
    },
    "field_action": {
      "trigger_actuator": true,
      "dosage_ml_per_sqm": 15.0,
      "isolation_required": true
    }
  }
}
```

---

## 🤖 Hardware Integration Flow

```
ESP32-CAM (Sensor Node) ───> Raspberry Pi SBC (Edge AI Brain) ───> ESP32-S3 Rover (Actuator Node)
Captures Crop JPEGs          Runs FastAPI + Qwen3.8-Max            Executes PID Navigation
POSTs to /diagnose           Encodes EdgeCommand Proto             Controls Motors & Sprayers
```

---

## ⚙️ Getting Started

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or standard `venv`
- DashScope API Key (`DASHSCOPE_API_KEY`)

### Setup
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/qwen_edge_agents.git
cd qwen_edge_agents

# Install dependencies using uv
uv sync

# Configure Environment Variables
# Set your DASHSCOPE_API_KEY in .env file
```

### Running the Comparison Harness
```bash
python compare.py
```

### Running the FastAPI Microservice
```bash
uvicorn main:app --reload --port 8000
```

### Running Unit Tests
```bash
python test_main.py
```
