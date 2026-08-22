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
├── diagnostics.proto       # Protobuf schema defining Location, DiagnosticData, FieldAction, EdgeCommand
├── diagnostics_pb2.py      # Compiled Python Protocol Buffer bindings
├── inference.py            # Dual-strategy inference engine calling Qwen3.8-Max multimodal API
├── actuator_rules.py       # Hardware actuation rules engine mapping (IssueType, Severity) to chemical/dosage/nozzles
├── simulated_sprayer_bot.py# Hardware simulation bot receiving location-aware Protobuf & triggering relays
├── main.py                 # FastAPI microservice wrapper providing /diagnose, /compare, and /dispatch
├── compare.py              # Side-by-side strategy benchmark & agreement reporting script
├── test_main.py            # Unit test suite verifying endpoints, rules engine, and hardware dispatch
└── test_images/            # Sample leaf dataset for edge testing
```

---

## 🚀 API Endpoints (`main.py`)

### 1. `GET /health`
Returns node status and system metadata.

### 2. `POST /diagnose`
Runs single-strategy inference on an uploaded image file or local image path.
* **Query Params**: `strategy=constrained` or `strategy=freeform`
* **Response**: Serialized `EdgeCommand` Protobuf JSON containing `DiagnosticData` and computed `FieldAction`.

### 3. `POST /compare`
Runs **both** strategies side-by-side against the same image and reports agreement.

### 4. `POST /dispatch` (Full Hardware Execution)
Receives image + scout agrover GPS location metadata (`latitude`, `longitude`, `zone_id`, `row_id`), runs Qwen AI diagnosis, evaluates chemical/dosage actuation rules, packages location-aware Protobuf, and dispatches to the spraying bot.

---

## 🤖 Hardware Integration Flow

```
ESP32-CAM (Scout Agrover) ───> Raspberry Pi (AI Edge Brain) ───> ESP32-S3 / ROS 2 (Spraying Bot)
Captures Leaf JPEG + GPS      Runs Qwen-VL + Actuator Rules       Receives Protobuf EdgeCommand
POSTs to /dispatch            Encodes Location-Aware Proto        Navigates Zone & Activates Pump Relays
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

---

## 🔀 Versioning, Collaboration & Experimentation

This repository follows standard software versioning and collaborative Git practices tailored for AI edge experimentation.

### Branching Strategy

- **`main`**: Production-ready, tested code and stable release tags (`vX.Y.Z`).
- **`feature/<feature-name>`**: New diagnostic features, API endpoints, or hardware protocols.
- **`experiment/<experiment-name>`**: Sandbox branches for testing new model parameters, prompt engineering, image preprocessing, or latency optimizations.

### Quick Workflow for Experiments

```bash
# 1. Create an isolated experiment branch from main
git checkout main
git pull origin main
git checkout -b experiment/vision-thresholds

# 2. Develop and test your changes
python compare.py

# 3. Commit clean changes
git add .
git commit -m "feat: evaluate bicubic vs bilinear image scaling"

# 4. Open a Pull Request on GitHub targeting main
```

For full details on semantic versioning, commit formats, and submitting Pull Requests, please consult [CONTRIBUTING.md](CONTRIBUTING.md).

