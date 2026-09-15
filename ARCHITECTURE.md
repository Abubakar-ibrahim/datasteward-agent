# Architecture

```mermaid
flowchart LR
    U[Analyst] --> UI[Streamlit UI]
    UI --> A[Strands Agent]
    A --> M[Qwen3 4B via Ollama\nor Amazon Bedrock]
    A --> T1[analyze_dataset]
    A --> T2[prepare_safe_outputs]
    A --> H[Strands HumanInTheLoop]
    H -->|Approve| T3[publish_final_dataset]
    H -->|Reject| A
    T1 --> Q[Profile + issues + score]
    T2 --> S[Safe-cleaned CSV]
    T2 --> R[Human-review queue]
    T3 --> F[Published safe-cleaned CSV]
    T3 --> J[Audit JSON]
```

## Human-centered boundary

`analyze_dataset` and `prepare_safe_outputs` are allow-listed for autonomous execution because they either inspect data or apply the narrowly defined safe action of removing exact duplicate rows into a new file. `publish_final_dataset` is not allow-listed, so Strands HumanInTheLoop interrupts the real agent before publication. The user explicitly approves or rejects that consequential action, after which the same agent run resumes.
