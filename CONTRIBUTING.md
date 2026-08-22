# Contributing to Qwen Edge Agents

Thank you for contributing! This guide outlines the development workflow, branching strategy, versioning policies, and procedures for running experiments and submitting changes.

---

## 1. Branching Strategy

To maintain a clean main history and encourage rapid experimentation, we follow a feature and experiment branch workflow:

### Branch Naming Conventions

- **`main`**: Production-ready code and stable releases. All changes to `main` must arrive via verified Pull Requests.
- **`feature/<feature-name>`**: New tools, diagnostic capabilities, API endpoints, or architecture upgrades.
  - Example: `feature/grpc-streaming-api`, `feature/onnx-quantization`
- **`experiment/<experiment-name>`**: Isolated sandbox branches for testing model prompts, vision thresholds, benchmark comparisons, or experimental algorithms.
  - Example: `experiment/qwen2.5-vl-7b-benchmark`, `experiment/resize-bicubic-vs-bilinear`
- **`fix/<bug-name>`**: Bug fixes for reported issues.
  - Example: `fix/protobuf-deserialization-null`

---

## 2. Experimentation & Collaboration Workflow

### Running an Experiment

1. **Create an Experiment Branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b experiment/my-idea
   ```
2. **Implement & Log Results**:
   - Save experiment test scripts or benchmark outputs (e.g. using `compare.py` or `resize_test_images.py`).
   - Commit code changes cleanly with descriptive commit messages.
3. **Propose Results**:
   - If the experiment succeeds and yields improved performance or accuracy, open a Pull Request using the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md).
   - Detail the benchmark numbers, accuracy impact, and latency changes in the PR description.

---

## 3. Versioning Policy

We use [Semantic Versioning (SemVer)](https://semver.org/): `vMAJOR.MINOR.PATCH`.

- **MAJOR (`v1.0.0`)**: Incompatible API or protobuf schema breaks.
- **MINOR (`v0.2.0`)**: Backward-compatible new features (e.g. new inference mode, added diagnostic field).
- **PATCH (`v0.1.1`)**: Backward-compatible bug fixes and documentation updates.

Git tags are created on `main` for release checkpoints:
```bash
git tag -a v0.1.0 -m "Initial release of Qwen edge diagnostic pipeline"
git push origin v0.1.0
```

---

## 4. Commit Guidelines

Follow standard Conventional Commits:

- `feat: add dual-image comparison in compare.py`
- `fix: resolve protobuf field mapping error`
- `docs: update setup and experimentation guide in README`
- `test: add unit tests for vision inference fallback`
- `refactor: optimize image preprocessing speed`

---

## 5. Submitting a Pull Request (PR)

1. Ensure unit tests pass locally:
   ```bash
   python test_main.py
   ```
2. Verify `.gitignore` rules prevent committing secrets or temporary output files (`.env`, `__pycache__`, etc.).
3. Open a PR on GitHub targetting the `main` branch.
4. Request review from project maintainers.
