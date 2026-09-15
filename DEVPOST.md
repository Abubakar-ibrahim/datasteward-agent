# DataSteward Agent — Devpost draft

## Inspiration
Data teams spend substantial time profiling messy datasets, finding duplicates, checking missing values, investigating anomalies, and preparing cleaned outputs. The repetitive parts are ideal for agents, but blindly changing or publishing data creates risk. DataSteward was built around a simple principle: **autonomous where safe, human approval where publication matters.**

## What it does
DataSteward accepts a CSV and uses a genuine Strands agent to analyze data quality, calculate a transparent 0–100 score, remove exact duplicates into a new safe-cleaned file, create a review queue for judgment-sensitive records, and pause before publishing final artifacts. A human approves or rejects publication through a Strands HumanInTheLoop intervention.

## How we built it
- Strands Agents SDK for agent orchestration and registered tools.
- Strands HumanInTheLoop for the publication approval boundary.
- Python/pandas/numpy for deterministic data-quality logic.
- Streamlit for the user interface.
- Qwen3 4B via Ollama for the recorded local demo.
- Amazon Bedrock provider support is implemented and configurable; account-level inference capacity was unavailable during the final submission window.

## Challenges
The main challenge was making the system both genuinely agentic and reliable on limited local hardware. We consolidated six narrow operations into three higher-level tools, reducing model round trips while preserving agent orchestration and the human approval boundary.

## Accomplishments
- Genuine Strands tool execution rather than UI-simulated agent steps.
- Explicit human gate for consequential publication.
- Deterministic, auditable quality metrics.
- Safe cleaning policy that never silently imputes missing data or deletes statistical anomalies.
- Provider-independent architecture supporting both local Ollama and Amazon Bedrock.

## What's next
Add richer schema/rule configuration, broader anomaly evaluation, record-linkage duplicate detection, dataset-specific policies, cloud deployment, and Amazon Bedrock/AgentCore execution when account inference capacity is available.
