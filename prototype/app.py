"""
LightningBoost · frontend/app.py  (MERGED PERFECT)
────────────────────────────────────────────────────
CRITICAL FIX vs CJ's original:
  ❌ CJ's version used hardcoded ram_percent=65.0, cpu_percent=42.0, disk_percent=58.0
     These numbers NEVER changed. Judges would notice immediately.
  ✅ This version pulls REAL live data from the backend API every refresh cycle.

Also adds:
  • Real-time sparklines from actual history
  • Routing decision display (shows local vs cloud per task)
  • Battery status (for laptops — the whole point of the project!)
  • Direct vLLM streaming chat for the AMD GPU demo
"""

import streamlit as st
import sys
import os
import time
import requests
import json
from datetime import datetime

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.config import CLOUD_BASE_URL, VLLM_BASE_URL, CLOUD_API_KEY
from shared.models import SystemMetrics

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LightningBoost ⚡",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html,body,[class*="css"]{ font-family: 'Segoe UI', sans-serif; }
.lb-header{ display:flex; align-items:center; gap:12px; padding:.5rem 0; }
.lb-header h1{ margin:0; font-size:1.8rem; font-weight:700; }
.tip-card{
  background:#12122a; border-left:3px solid #6366f1;
  border-radius:0 8px 8px 0; padding:.75rem 1rem;
  margin-bottom:.5rem; font-size:.9rem; line-height:1.5;
}
.proc-chip{ font-size:.78rem; color:#888; line-height:1.8; }
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────
if "ram_hist"  not in st.session_state: st.session_state.ram_hist  = []
if "cpu_hist"  not in st.session_state: st.session_state.cpu_hist  = []
if "disk_hist" not in st.session_state: st.session_state.disk_hist = []
if "task_log"  not in st.session_state: st.session_state.task_log  = []

# ─── API helpers ──────────────────────────────────────────────────────────────

HEADERS = {"X-API-Key": CLOUD_API_KEY} if CLOUD_API_KEY else {}

def api_get(path: str, timeout: int = 5):
    try:
        r = requests.get(f"{CLOUD_BASE_URL}{path}", headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def api_post(path: str, body: dict, timeout: int = 60):
    try:
        r = requests.post(
            f"{CLOUD_BASE_URL}{path}", json=body, headers=HEADERS, timeout=timeout
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def check_vllm() -> bool:
    try:
        r = requests.get(f"{VLLM_BASE_URL}/health", timeout=4)
        return r.ok
    except Exception:
        return False

# ─── Chart helpers ────────────────────────────────────────────────────────────

def gauge(value: float, title: str, color: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 13, "color": "#ccc"}},
        number={"suffix": "%", "font": {"size": 24, "color": "#fff"}},
        gauge={
            "axis":  {"range": [0, 100], "tickcolor": "#555"},
            "bar":   {"color": color},
            "bgcolor": "#1a1a2e",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  70], "color": "#14142a"},
                {"range": [70, 85], "color": "#2a1a0a"},
                {"range": [85,100], "color": "#2a0a0a"},
            ],
        },
    ))
    fig.update_layout(
        height=170, margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def sparkline(values, color: str) -> go.Figure:
    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
    ))
    fig.update_layout(
        height=55, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0,100]),
    )
    return fig

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚡ LightningBoost")
    st.caption("MeowMission · From Meows to the Moon")
    st.divider()

    backend_ok = api_get("/health") is not None
    vllm_ok    = check_vllm()

    st.markdown(f"**Cloud backend:** {'✅ Connected' if backend_ok else '❌ Offline'}")
    st.markdown(f"**vLLM (AMD GPU):**  {'✅ Connected' if vllm_ok    else '❌ Offline'}")
    st.divider()

    refresh = st.slider("Refresh (s)", 2, 15, 3)
    auto    = st.toggle("Auto-refresh", value=True)
    st.divider()
    st.caption(f"Backend: `{CLOUD_BASE_URL}`")
    st.caption(f"vLLM:    `{VLLM_BASE_URL}`")

# ─── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="lb-header">
  <span style="font-size:2rem">⚡</span>
  <div><h1>LightningBoost</h1></div>
</div>
""", unsafe_allow_html=True)

if not backend_ok:
    st.error("❌ Backend offline. Run `python cloud_backend/server.py` first.")

# ─── Tabs ─────────────────────────────────────────────────────────────────────

t_monitor, t_tasks, t_vllm, t_history = st.tabs([
    "📊 Live Monitor", "🚀 Submit Task", "🤖 AMD GPU Chat", "📋 History"
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 · LIVE MONITOR  (real data — no hardcoding!)
# ═══════════════════════════════════════════════════════════════════════════════

with t_monitor:
    # ── Fetch REAL metrics from backend API ───────────────────────────────────
    metrics_data = api_get("/metrics")  # FastAPI returns live psutil data

    if not metrics_data:
        st.info("Waiting for backend metrics…")
        st.stop()

    # Update sparkline history
    ram_pct  = metrics_data.get("ram_percent",  0.0)
    cpu_pct  = metrics_data.get("cpu_percent",  0.0)
    disk_pct = metrics_data.get("disk_percent", 0.0)
    st.session_state.ram_hist.append(ram_pct)
    st.session_state.cpu_hist.append(cpu_pct)
    st.session_state.disk_hist.append(disk_pct)
    # Keep last 60 samples
    for k in ("ram_hist", "cpu_hist", "disk_hist"):
        st.session_state[k] = st.session_state[k][-60:]

    # ── Severity badge ─────────────────────────────────────────────────────────
    sev = metrics_data.get("severity", "ok")
    sev_map = {"ok": "✅ System OK", "warning": "⚠️ Warning", "heavy": "🔴 Heavy load"}
    ts  = metrics_data.get("timestamp", "")
    st.markdown(f"**{sev_map.get(sev, sev)}** &nbsp; `{ts[:19]}`")

    # ── Gauges ─────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        color = "#f87171" if ram_pct > 85 else "#fb923c" if ram_pct > 70 else "#4ade80"
        st.plotly_chart(gauge(ram_pct, "RAM", color), use_container_width=True)
    with c2:
        color = "#f87171" if cpu_pct > 80 else "#fb923c" if cpu_pct > 60 else "#4ade80"
        st.plotly_chart(gauge(cpu_pct, "CPU", color), use_container_width=True)
    with c3:
        color = "#fb923c" if disk_pct > 80 else "#facc15"
        st.plotly_chart(gauge(disk_pct, "Disk", color), use_container_width=True)
    with c4:
        ram_avail = metrics_data.get("ram_available_mb", 0)
        ram_total_mb = metrics_data.get("ram_used_mb", 0) + ram_avail
        st.metric("RAM Available", f"{ram_avail/1024:.1f} GB",
                  f"{ram_total_mb/1024:.1f} GB total")
        procs = metrics_data.get("process_count", 0)
        st.metric("Processes", procs)
        bat = metrics_data.get("battery_percent")
        if bat is not None:
            plugged = "🔌" if metrics_data.get("battery_plugged") else "🔋"
            st.metric("Battery", f"{bat}%", plugged)

    # ── Sparklines ─────────────────────────────────────────────────────────────
    st.markdown("#### Trend (last 60 samples)")
    sp1, sp2, sp3 = st.columns(3)
    with sp1:
        st.caption("RAM %")
        st.plotly_chart(sparkline(st.session_state.ram_hist,  "rgb(99,102,241)"), use_container_width=True)
    with sp2:
        st.caption("CPU %")
        st.plotly_chart(sparkline(st.session_state.cpu_hist,  "rgb(251,146,60)"), use_container_width=True)
    with sp3:
        st.caption("Disk %")
        st.plotly_chart(sparkline(st.session_state.disk_hist, "rgb(250,204,21)"), use_container_width=True)

    # ── Top processes ──────────────────────────────────────────────────────────
    st.markdown("#### Top RAM consumers")
    top_procs = metrics_data.get("top_processes", [])
    if top_procs:
        df = pd.DataFrame(top_procs, columns=["Process", "PID", "RAM (MB)"])
        df["RAM (MB)"] = df["RAM (MB)"].round(1)
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    # ── Offload recommendation ─────────────────────────────────────────────────
    if ram_pct > 85:
        st.error("🔴 **Offload recommended** — RAM is critical. Heavy tasks will be routed to AMD cloud automatically.")
    elif ram_pct > 70:
        st.warning("⚠️ **RAM elevated** — heavy tasks will be offloaded to AMD cloud.")
    else:
        st.success("✅ **System healthy** — tasks can run locally.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 · SUBMIT TASK
# ═══════════════════════════════════════════════════════════════════════════════

with t_tasks:
    st.markdown("### 🚀 Submit a task to LightningBoost")
    st.caption("The AI router automatically decides: local execution or AMD cloud GPU.")

    task_options = {
        "💬 Text generation":          "TEXT_GENERATION",
        "📝 Summarisation":            "TEXT_GENERATION",
        "💻 Code generation":          "TEXT_GENERATION",
        "❓ Question answering":       "TEXT_GENERATION",
        "🔢 Embeddings":               "EMBEDDING",
        "🏷️ Image classification":    "IMAGE_CLASSIFICATION",
        "⚡ Lightweight (always local)":"LIGHTWEIGHT",
    }

    label   = st.selectbox("Task type", list(task_options.keys()))
    ttype   = task_options[label]
    desc    = st.text_input("Description", placeholder="What should this task do?")
    prompt  = st.text_area("Input / Prompt", height=150,
                           placeholder="Type your prompt or text here…")
    max_tok = st.slider("Max tokens", 64, 2048, 256) if ttype == "TEXT_GENERATION" else 256

    if st.button("⚡ Run Task", type="primary", disabled=not (desc and prompt)):
        with st.spinner("Routing and executing…"):
            result = api_post("/api/v1/tasks", {
                "task_type":   ttype,
                "description": desc,
                "input_data":  {"prompt": prompt, "max_tokens": max_tok},
            })
        if result:
            task_id = result.get("task_id", "")
            st.success(f"Task submitted — ID: `{task_id[:8]}`")
            # Poll for result
            for _ in range(30):
                time.sleep(2)
                status = api_get(f"/api/v1/tasks/{task_id}", timeout=5)
                if status and status.get("status") in ("completed", "failed"):
                    break
            if status and status.get("status") == "completed":
                loc = status.get("execution_location", "?")
                st.success(f"✅ Done · Ran on **{loc.upper()}**"
                           + (" ☁️ AMD GPU" if loc == "cloud" else " 💻 local"))
                result_data = status.get("result", {})
                st.markdown("**Result:**")
                st.markdown(result_data.get("response", str(result_data)))
                st.session_state.task_log.insert(0, status)
            else:
                st.error(f"Failed: {status.get('error', 'unknown') if status else 'timeout'}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 · AMD GPU CHAT (direct vLLM streaming — best demo for hackathon!)
# ═══════════════════════════════════════════════════════════════════════════════

with t_vllm:
    st.markdown("### 🤖 Direct AMD GPU Chat")
    st.caption("Sends prompts directly to vLLM running on AMD MI300X via ROCm")

    if not vllm_ok:
        st.warning("vLLM is offline. Start it with: `docker compose --profile gpu up vllm`")
    else:
        st.success("✅ vLLM connected — running on AMD GPU via ROCm")

    vllm_model = st.text_input("Model", value="meta-llama/Llama-3.1-8B-Instruct")
    vllm_prompt = st.text_area("Prompt", height=120,
                               placeholder="Ask the AMD GPU something heavy…")
    vllm_tokens = st.slider("Max tokens", 64, 2048, 512)

    if st.button("🚀 Send to AMD GPU", type="primary", disabled=not vllm_prompt):
        with st.spinner("Generating on AMD MI300X…"):
            start = time.time()
            try:
                resp = requests.post(
                    f"{VLLM_BASE_URL}/v1/chat/completions",
                    json={
                        "model":      vllm_model,
                        "messages":   [{"role": "user", "content": vllm_prompt}],
                        "max_tokens": vllm_tokens,
                    },
                    timeout=120,
                )
                resp.raise_for_status()
                data    = resp.json()
                text    = data["choices"][0]["message"]["content"]
                elapsed = round(time.time() - start, 2)
                st.success(f"Response in {elapsed}s on AMD GPU:")
                st.markdown(text)
            except Exception as e:
                st.error(f"vLLM error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 · TASK HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

with t_history:
    st.markdown("### 📋 Task history")

    # Fetch from backend (not just session state)
    hist = api_get("/api/v1/tasks")
    tasks = (hist or {}).get("tasks", [])

    if tasks:
        rows = []
        for t in tasks:
            rows.append({
                "ID":       t.get("id","")[:8],
                "Type":     t.get("task_type",""),
                "Status":   t.get("status",""),
                "Location": t.get("execution_location","?"),
                "Created":  t.get("created_at","")[:19],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Local/cloud pie chart
        locs = [t.get("execution_location","unknown") for t in tasks if t.get("execution_location")]
        if locs:
            vc = pd.Series(locs).value_counts()
            fig = px.pie(values=vc.values, names=vc.index, hole=0.4,
                         title="Task execution location")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tasks yet — submit one in the 'Submit Task' tab.")


# ─── Auto-refresh ─────────────────────────────────────────────────────────────
if auto:
    time.sleep(refresh)
    st.rerun()
