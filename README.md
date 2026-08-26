# MiRIHI Qwen Edge Diagnostic Agent

> Autonomous edge crop disease diagnostic microservice powered by **Qwen3.8-Max** with a dual-strategy classification pipeline, Protocol Buffer command wrapping, and hardware actuation mapping.

---

## 🌟 Overview & Purpose

**MiRIHI Qwen Edge Agent** is an edge intelligence microservice designed for autonomous agricultural rovers and field monitoring nodes. It analyzes crop leaf images captured by onboard cameras (e.g., ESP32-CAM nodes), runs multimodal AI diagnostics via **Qwen3.8-Max**, and packages diagnostic findings into structured **Protocol Buffer (`EdgeCommand`)** messages to trigger immediate physical field actions (such as automated spraying, isolation alerts, or routine logging).

---

## 🔬 Core Design: Constrained Taxonomy Classification

The inference pipeline is implemented in [`inference.py`](file:///c:/Users/Administrator/Desktop/qwen_edge_agents/inference.py). It prompts **Qwen3.8-Max** to select directly from a fixed closed taxonomy of `IssueType` enum values and return strict JSON — keeping the output tightly coupled to downstream protobuf parsing with zero ambiguity.

```
                           ┌───────────────────────────────┐
                           │      Crop Leaf Image          │
                           └───────────────┬───────────────┘
                                           │
                              ┌────────────▼────────────┐
                              │   Constrained Prompt    │
                              │   (JSON Taxonomy)       │
                              └────────────┬────────────┘
                                           │
                              Strict JSON Enum Output
                              {"issue_type": "BLIGHT",
                               "severity": "HIGH",
                               "confidence": 0.92, ...}
                                           │
                              ┌────────────▼────────────┐
                              │    DiagnosticData       │
                              │   Protobuf Message      │
                              └─────────────────────────┘
```

### Constrained Taxonomy (`constrained_diagnose`)
* **How it works**: Prompts Qwen3.8-Max to pick from `BLIGHT`, `PEST_INFESTATION`, `NUTRIENT_DEFICIENCY`, `FUNGAL_INFECTION`, `VIRAL_INFECTION`, `WATER_STRESS`, or `HEALTHY` and return a JSON object with `issue_type`, `severity`, `confidence`, and `description`.
* **Why constrained**: Zero post-processing needed, direct JSON deserialization into proto, no keyword mapping ambiguity — safe for real-time hardware actuation triggers.
* **Resilience**: The parser strips markdown code fences (` ```json `) so the model never breaks parsing even when it wraps its output.

---

## 🛠️ Codebase Architecture

```
qwen_edge_agents/
├── diagnostics.proto       # Protobuf schema: Location, DiagnosticData, FieldAction, EdgeCommand
├── diagnostics_pb2.py      # Compiled Python Protocol Buffer bindings
├── inference.py            # Constrained inference engine calling Qwen3.8-Max multimodal API
├── actuator_rules.py       # Rules engine mapping (IssueType, Severity) → chemical/dosage/nozzle
├── simulated_sprayer_bot.py# Hardware simulation bot receiving location-aware Protobuf EdgeCommands
├── main.py                 # FastAPI microservice: /health, /diagnose, /dispatch
├── compare.py              # Constrained inference batch test runner across image set
├── test_main.py            # Unit test suite: endpoints, rules engine, hardware dispatch
└── test_images/            # Sample leaf dataset for edge testing
```

---

## 🚀 API Endpoints (`main.py`)

### 1. `GET /health`
Returns node status and system metadata.

### 2. `POST /diagnose`
Runs constrained taxonomy inference on an uploaded image file or local image path.
* **Body**: `file` (multipart upload) or `image_path` (form string)
* **Response**: Serialized `EdgeCommand` Protobuf JSON containing `DiagnosticData` and computed `FieldAction`.

### 3. `POST /dispatch` (Full Hardware Execution)
Receives image + scout agrover GPS location metadata (`latitude`, `longitude`, `zone_id`, `row_id`), runs Qwen3.8-Max diagnosis, evaluates chemical/dosage actuation rules, packages location-aware Protobuf, and dispatches to the spraying bot.



## 🤖 Hardware Integration Flow

```
ESP32-CAM (Scout Agrover) ───> Raspberry Pi (AI Edge Brain) ───> ESP32-S3 / ROS 2 (Spraying Bot)
Captures Leaf JPEG + GPS      Runs Qwen3.8-Max + Actuator Rules  Receives Protobuf EdgeCommand
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

