# DataSteward Agent v0.6.1

**Autonomous where safe. Human approval where publication matters.**

DataSteward Agent is a human-centered data-quality operator built with the **Strands Agents SDK**. It profiles CSV data, detects missingness/duplicates/rule failures/anomalies, calculates a transparent quality score, applies only safe cleaning, creates a human-review queue, and pauses the real Strands agent loop before final publication.

## Why v0.6.1

v0.6.1 is optimized for a reliable local hackathon demo. Instead of asking a small local model to coordinate six narrow tools, the agent now uses three higher-level tools:

1. `analyze_dataset` — profile + issue detection + quality scoring.
2. `prepare_safe_outputs` — exact-duplicate removal + human-review queue.
3. `publish_final_dataset` — human-gated final export + audit report.

The orchestration is still genuinely agentic: a Strands `Agent` receives the task, invokes registered `@tool` functions, hits a Strands `HumanInTheLoop` intervention at publication, and resumes the same paused agent after the user's decision.

## Model providers

The same Strands workflow supports:

- **Ollama / Qwen3 4B** — default local demo provider.
- **Amazon Bedrock** — optional AWS provider when inference quota is available.

The provider swap does not change the tools, safety policy, or human approval boundary.

## Quick start on macOS

Install/start Ollama and ensure Qwen is available:

```bash
ollama serve
```

In another terminal:

```bash
ollama list
```

You should see `qwen3:4b`. Then:

```bash
cd datasteward-agent-v0.6.1
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

If you already have a working v0.5 virtual environment, you can use that instead of reinstalling everything.

## Registered Strands tools

- `analyze_dataset`
- `prepare_safe_outputs`
- `publish_final_dataset` — protected by Strands HumanInTheLoop

## Safety policy

- Exact duplicate removal is the only automatic destructive change.
- Missing values are preserved and queued for human review.
- Rule failures are preserved and queued for human review.
- Statistical anomalies are preserved and queued for human review.
- The source CSV is never overwritten.
- Final publication requires explicit human approval.

## Bundled demo

The synthetic demo CSV has 82 rows, 2 missing cells, 2 exact duplicate rows, and one deliberately injected numeric anomaly. Preflight quality score is 99.0/100. The bundled deterministic smoke test detects the single injected anomaly with precision/recall/F1 of 1.0. This is a focused synthetic validation, not a real-world benchmark claim.

## Expected approved-run outputs

- `outputs/safe_cleaned.csv`
- `outputs/review_queue.csv`
- `outputs/cleaned.csv`
- `outputs/audit.json`

## Optional Amazon Bedrock configuration

When Bedrock quota is available:

```bash
export DATASTEWARD_MODEL_PROVIDER=bedrock
export AWS_REGION=us-west-2
export BEDROCK_MODEL_ID=us.amazon.nova-micro-v1:0
```

Use standard AWS SDK/CLI credentials; never commit credentials to the repository.

## Hackathon

Built for the AWS **Agents for Humans** Hackathon, Professional Agents track. The demo uses Strands Agents and Strands Human-in-the-Loop end-to-end. Amazon Bedrock support remains implemented, while Ollama/Qwen provides a reliable local inference fallback when account-level Bedrock capacity is unavailable.
