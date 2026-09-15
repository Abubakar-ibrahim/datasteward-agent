from pathlib import Path
import sys
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from quality import profile_csv, detect_issues, quality_score

st.set_page_config(page_title="DataSteward Agent v0.6.1", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 3rem; max-width: 1250px;}
h1, h2, h3 {letter-spacing: -0.02em;}
[data-testid="stMetricValue"] {font-size: 2rem;}
.ds-subtle {color:#666;font-size:1.03rem;}
.ds-step {border:1px solid #e7e7e7;border-radius:14px;padding:14px 16px;background:#fafafa;min-height:86px;}
.ds-card {border:1px solid #e8e8e8;border-radius:14px;padding:16px 18px;background:white;}
.ds-safe {border:1px solid #d8eadf;background:#f4fbf6;border-radius:12px;padding:14px 16px;}
.ds-review {border:1px solid #efe2b7;background:#fffaf0;border-radius:12px;padding:14px 16px;}
.ds-live {border:1px solid #c9dcff;background:#f6f9ff;border-radius:12px;padding:14px 16px;}
</style>
""", unsafe_allow_html=True)

st.title("DataSteward Agent")
st.markdown('<div class="ds-subtle">A genuine Strands agent loop for data quality: autonomous where safe, human approval where judgment or publication matters.</div>', unsafe_allow_html=True)
st.write("")

steps = [
    ("1","Upload","Provide a CSV"),
    ("2","Agent","Model chooses tools"),
    ("3","Act","Safe tools run"),
    ("4","Approve","Human gate pauses agent"),
    ("5","Export","Agent resumes and publishes"),
]
cols = st.columns(5)
for c,(n,title,desc) in zip(cols,steps):
    with c:
        st.markdown(f'<div class="ds-step"><b>{n}. {title}</b><br><span style="color:#777">{desc}</span></div>', unsafe_allow_html=True)

st.write("")
use_demo = st.toggle("Use bundled demo dataset", value=True)
uploaded = None if use_demo else st.file_uploader("Upload a CSV", type=["csv"])

if use_demo:
    active_path = "data/demo_registry.csv"
    st.caption("Using bundled synthetic demo data.")
elif uploaded:
    p = Path("outputs/uploaded.csv")
    p.parent.mkdir(exist_ok=True)
    p.write_bytes(uploaded.getvalue())
    active_path = str(p)
else:
    active_path = None

if active_path:
    profile = profile_csv(active_path)
    detected = detect_issues(active_path)
    score = quality_score(active_path)

    st.subheader("Dataset preview")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Quality score", f'{score["overall_score"]}/100')
    c2.metric("Rows", profile["rows"])
    c3.metric("Columns", profile["columns"])
    c4.metric("Missing cells", profile["missing_cells"])
    c5.metric("Duplicates", profile["duplicate_rows"])
    st.caption("These preview metrics are deterministic preflight checks. They are not labeled as agent activity.")

    st.divider()
    st.subheader("Live Strands agent")
    st.markdown('<div class="ds-live"><b>What makes v0.6.1 agentic:</b> A real Strands Agent executes three higher-level tools: analysis, safe preparation, and publication. Qwen3 4B runs locally through Ollama for a reliable demo; Amazon Bedrock remains a configurable provider. Strands HumanInTheLoop pauses the actual agent loop before publication, and the same agent instance resumes after your decision.</div>', unsafe_allow_html=True)

    if "agent_result" not in st.session_state:
        st.session_state.agent_result = None
        st.session_state.agent_obj = None
        st.session_state.trace = []
        st.session_state.final_text = None
        st.session_state.interrupt_id = None
        st.session_state.interrupt_reason = None

    if st.button("Run DataSteward Agent", type="primary", use_container_width=True):
        try:
            from agent import start_run, get_trace, result_text
            with st.spinner("The Strands agent is reasoning and selecting tools..."):
                agent_obj, result = start_run(active_path)
            st.session_state.agent_obj = agent_obj
            st.session_state.agent_result = result
            st.session_state.trace = get_trace()
            st.session_state.final_text = None
            if getattr(result, "stop_reason", None) == "interrupt":
                intr = result.interrupts[0]
                st.session_state.interrupt_id = intr.id
                st.session_state.interrupt_reason = str(intr.reason)
            else:
                st.session_state.final_text = result_text(result)
                st.session_state.interrupt_id = None
                st.session_state.interrupt_reason = None
        except Exception as e:
            st.error(f"Live agent could not start: {e}")
            st.info("For Ollama, confirm `ollama serve` is running and `ollama list` shows qwen3:4b. For Bedrock, confirm AWS model access and quota.")

    if st.session_state.trace:
        st.subheader("Verified tool execution trace")
        trace_df = pd.DataFrame([
            {"#": i+1, "Strands tool": item["tool"], "Observed execution": item["summary"]}
            for i,item in enumerate(st.session_state.trace)
        ])
        st.dataframe(trace_df, use_container_width=True, hide_index=True)
        st.caption("This table is populated inside the registered @tool functions only when the Strands agent actually executes them.")

    if st.session_state.interrupt_id:
        st.subheader("Human approval required")
        st.warning(st.session_state.interrupt_reason or "The agent is paused before a consequential tool call.")
        st.write("The original source remains unchanged. Approving lets the same paused Strands agent resume and publish the safe-cleaned dataset plus an audit report. Judgment-sensitive rows remain documented in the review queue.")
        a,b = st.columns(2)
        if a.button("Approve publication", type="primary", use_container_width=True):
            try:
                from agent import resume_run, get_trace, result_text
                with st.spinner("Resuming the same Strands agent..."):
                    result = resume_run(st.session_state.agent_obj, st.session_state.interrupt_id, True)
                st.session_state.agent_result = result
                st.session_state.trace = get_trace()
                st.session_state.final_text = result_text(result)
                st.session_state.interrupt_id = None
                st.session_state.interrupt_reason = None
                st.rerun()
            except Exception as e:
                st.error(f"Could not resume agent: {e}")
        if b.button("Reject publication", use_container_width=True):
            try:
                from agent import resume_run, get_trace, result_text
                with st.spinner("Returning your rejection to the agent..."):
                    result = resume_run(st.session_state.agent_obj, st.session_state.interrupt_id, False)
                st.session_state.agent_result = result
                st.session_state.trace = get_trace()
                st.session_state.final_text = result_text(result)
                st.session_state.interrupt_id = None
                st.session_state.interrupt_reason = None
                st.rerun()
            except Exception as e:
                st.error(f"Could not resume agent: {e}")

    if st.session_state.final_text:
        st.subheader("Agent result")
        st.write(st.session_state.final_text)

    artifacts = [
        ("outputs/safe_cleaned.csv", "Safe-cleaned intermediate CSV", "text/csv"),
        ("outputs/review_queue.csv", "Human-review queue CSV", "text/csv"),
        ("outputs/cleaned.csv", "Published safe-cleaned CSV", "text/csv"),
        ("outputs/audit.json", "Audit report JSON", "application/json"),
    ]
    existing = [(p,l,m) for p,l,m in artifacts if Path(p).exists()]
    if existing:
        st.subheader("Artifacts created")
        cols = st.columns(min(4, len(existing)))
        for col,(p,label,mime) in zip(cols, existing):
            with col:
                st.download_button(label, Path(p).read_bytes(), file_name=Path(p).name, mime=mime, use_container_width=True)

    st.divider()
    with st.expander("Architecture and model configuration"):
        st.code("User → Streamlit → Strands Agent → Ollama/Qwen3 4B (or Bedrock) → 3 tools → HITL interrupt → human decision → same agent resumes → artifacts")
        st.write("Default provider: `ollama`, model: `qwen3:4b`, endpoint: `http://localhost:11434`.")
        st.write("Switch providers with `DATASTEWARD_MODEL_PROVIDER=ollama|bedrock`. Bedrock settings use `AWS_REGION` and `BEDROCK_MODEL_ID`.")
else:
    st.info("Upload a CSV or switch on the bundled demo dataset to begin.")
