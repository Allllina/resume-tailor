# Contributing to Resume Tailor

Thank you for your interest in improving Resume Tailor! This is a concise guide to help you get started with bug reporting, feature suggestions, and our development workflow.

---

## 1. Filing Bugs and Feature Requests

We use GitHub Issues to track feedback:
* **Bugs:** Select the **Bug Report** template. Ensure you provide clear reproduction steps, environment details (Node/Python version, OS), and logs or screenshots.
* **Features:** Select the **Feature Request** template. Describe the problem you are solving, the proposed solution, and any alternatives you've considered.

---

## 2. Dev Workflow

Resume Tailor is built with a Python backend and a React/TypeScript frontend. Follow these steps to set up your environment:

1. **Seed Sample Data:** Populates gitignored asset paths from anonymized samples.
   ```bash
   make seed-sample
   ```
2. **Environment Variables:** Create a `.env` file in `packages/harness/` or customize as needed (refer to the README for details).
3. **Start the Backend:** Starts the FastAPI harness backend on port `8001`.
   ```bash
   make backend
   ```
4. **Start the Frontend UI:** Starts the UI development server on port `8080`.
   ```bash
   make ui
   ```

---

## 3. Contract-First Protocol

We follow a contract-first protocol where frontend types are derived directly from the backend API/schema specifications:
* **Check Drift:** Verify that the current schema, types, and mock fixtures are synchronized:
  ```bash
  make check-contracts
  # Executes scripts/check_contracts.py
  ```
* **Generate Types:** If you modify backend schemas under `contracts/schemas/`, regenerate the UI TypeScript definitions:
  ```bash
  make gen-types
  # Executes scripts/gen_ts_types.py (updates ui/src/types/generated.ts)
  ```

---

## 4. Running Tests

Before committing, ensure all tests pass:
* **Run Backend Tests:** Run all Python backend unit & integration tests.
  ```bash
  make test
  ```
* **Run Unit Tests Only:** Fast feedback loop for unit tests.
  ```bash
  make test-quick
  ```

---

## 5. CI Gates

Every Pull Request must pass the following 4 automated CI workflows to be eligible for merging:

1. **`tests` (Backend Gates):** Runs backend linting (`ruff`, `mypy`) and all unit/integration tests with `pytest`.
2. **`ui` (Frontend Gates):** Typechecks, lints, and builds the frontend React application.
3. **`contracts` (Contract Drift Gate):** Runs `scripts/check_contracts.py` to prevent structural drift between the frontend and backend.
4. **`playwright` (E2E Gates):** Performs end-to-end integration tests using Playwright.
