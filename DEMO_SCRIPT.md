# Final demo script (target: 2–3 minutes)

## 1. Problem — 20 seconds
"Data quality work is repetitive, but fully autonomous cleaning can be risky. DataSteward is an agent that acts autonomously only where the action is safe, and asks a human before consequential publication."

## 2. Architecture — 20 seconds
"The application uses the Strands Agents SDK. For this demo the Strands agent uses Qwen3 4B through Ollama. The same code also supports Amazon Bedrock. Three registered tools keep the workflow reliable: analyze, prepare safe outputs, and publish. Publication is protected by Strands HumanInTheLoop."

## 3. Run — 60–90 seconds
- Show bundled demo selected.
- Point to preflight metrics: 82 rows, 2 missing cells, 2 duplicates, quality 99.0.
- Click **Run DataSteward Agent**.
- Show the verified Strands tool execution trace.
- Highlight that only exact duplicates are automatically removed and review-sensitive rows are preserved.
- When the human approval panel appears, explain that the actual Strands loop is paused.
- Click **Approve publication**.
- Show `cleaned.csv`, `review_queue.csv`, and `audit.json` appearing.

## 4. Close — 20 seconds
"DataSteward reduces repetitive data-quality work without hiding judgment calls. The principle is simple: autonomous where safe, human approval where publication matters."

## Accuracy note
Do not say the recorded demo ran on Bedrock unless it actually did. Say the app supports Bedrock, while the recorded demo uses Qwen3 4B through Ollama because the AWS account's Bedrock inference quota was unavailable during the submission window.
