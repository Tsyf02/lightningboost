"""
LightningBoost — Frontend Streamlit Application
Design System: Dark OLED | Space Grotesk + DM Sans | Green CTA
Critical Fixes Applied:
  - psutil removed (runs on server, not user machine)
  - Local Agent stats panel (user pastes stats OR manual sliders)
  - Screenshot upload → Qwen3-VL-32B route (port 8080)
  - Text queries → Qwen3.5-35B-A3B fast route (port 8081)
  - Streaming responses via st.write_stream
  - Job polling via job_id (no fire-and-forget)
  - Qwen </think> token stripped before display
  - All URLs from os.environ (no hardcoded IPs)
  - FastAPI async backend assumed
"""

import streamlit as st
import os
import time
import base64
import requests
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from shared.config import (
    VL_MODEL_URL, TEXT_MODEL_URL

)



# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LightningBoost",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design System: Dark OLED + Space Grotesk/DM Sans ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:wght@400;500;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0F172A;
    color: #F8FAFC;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Space Grotesk', sans-serif !important;
    color: #F8FAFC !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #1E293B !important;
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px 20px;
    transition: border-color 0.2s ease;
}
[data-testid="stMetric"]:hover { border-color: #22C55E; }
[data-testid="stMetricLabel"]  { color: #94A3B8 !important; font-size: 13px !important; }
[data-testid="stMetricValue"]  { color: #F8FAFC !important; font-family: 'Space Grotesk', sans-serif !important; }
[data-testid="stMetricDelta"]  { font-size: 12px !important; }

/* ── Buttons ── */
.stButton > button {
    background: #22C55E !important;
    color: #0F172A !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    cursor: pointer !important;
    transition: background 0.2s ease, transform 0.15s ease !important;
}
.stButton > button:hover  { background: #16A34A !important; transform: translateY(-1px) !important; }
.stButton > button:active { transform: translateY(0) !important; }
.stButton > button:disabled { background: #334155 !important; color: #64748B !important; cursor: not-allowed !important; }

/* ── Secondary button ── */
.btn-secondary > button {
    background: #334155 !important;
    color: #F8FAFC !important;
}
.btn-secondary > button:hover { background: #475569 !important; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #F8FAFC !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #22C55E !important;
    box-shadow: 0 0 0 2px rgba(34,197,94,0.2) !important;
    outline: none !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #1E293B;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #94A3B8 !important;
    border-radius: 7px !important;
    padding: 8px 18px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.stTabs [aria-selected="true"] {
    background: #0F172A !important;
    color: #22C55E !important;
}

/* ── Cards ── */
.lb-card {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    transition: border-color 0.2s ease;
}
.lb-card:hover { border-color: #475569; }
.lb-card-accent { border-left: 3px solid #22C55E; }

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'Space Grotesk', sans-serif;
    letter-spacing: 0.03em;
}
.badge-green  { background: rgba(34,197,94,0.15);  color: #22C55E; }
.badge-blue   { background: rgba(59,130,246,0.15); color: #60A5FA; }
.badge-yellow { background: rgba(234,179,8,0.15);  color: #FACC15; }
.badge-red    { background: rgba(239,68,68,0.15);  color: #F87171; }
.badge-gray   { background: rgba(100,116,139,0.15);color: #94A3B8; }

/* ── Progress bar ── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #22C55E, #16A34A) !important;
}

/* ── Alerts ── */
.stSuccess { background: rgba(34,197,94,0.1)  !important; border-left: 3px solid #22C55E !important; color: #F8FAFC !important; }
.stError   { background: rgba(239,68,68,0.1)  !important; border-left: 3px solid #F87171 !important; color: #F8FAFC !important; }
.stWarning { background: rgba(234,179,8,0.1)  !important; border-left: 3px solid #FACC15 !important; color: #F8FAFC !important; }
.stInfo    { background: rgba(59,130,246,0.1) !important; border-left: 3px solid #60A5FA !important; color: #F8FAFC !important; }

/* ── Plotly dark bg ── */
.js-plotly-plot .plotly .bg { fill: #1E293B !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #1E293B;
    border: 2px dashed #334155;
    border-radius: 12px;
    padding: 16px;
    transition: border-color 0.2s ease;
}
[data-testid="stFileUploader"]:hover { border-color: #22C55E; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #334155 !important; border-radius: 8px !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] > div { border-top-color: #22C55E !important; }

/* ── Divider ── */
hr { border-color: #334155 !important; }

/* ── Radio ── */
.stRadio > div { gap: 12px !important; }
.stRadio label { cursor: pointer !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar       { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0F172A; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "task_history":    [],
        "agent_stats":     {},          # populated by local_agent.py or manual sliders
        "last_tips":       "",
        "active_job_id":   None,
        "stream_output":   "",
        "vl_job_id":       None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Utility helpers ───────────────────────────────────────────────────────────

PLOTLY_DARK = dict(
    paper_bgcolor="#1E293B",
    plot_bgcolor="#1E293B",
    font_color="#CBD5E1",
    xaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
    yaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
)

def _badge(text: str, variant: str = "gray") -> str:
    return f'<span class="badge badge-{variant}">{text}</span>'

def _status_badge(status: str) -> str:
    mapping = {
        "completed": ("DONE",    "green"),
        "running":   ("RUNNING", "blue"),
        "pending":   ("PENDING", "yellow"),
        "queued":    ("QUEUED",  "yellow"),
        "failed":    ("FAILED",  "red"),
    }
    label, variant = mapping.get(status.lower(), (status.upper(), "gray"))
    return _badge(label, variant)

def _severity_badge(severity: str) -> str:
    m = {"low": "green", "medium": "yellow", "high": "red"}
    return _badge(severity.upper(), m.get(severity, "gray"))


def strip_qwen_thinking(raw: str) -> str:
    """
    Qwen3-Thinking models output </think> without opening tag.
    Strip everything before and including </think> before showing to user.
    """
    if "</think>" in raw:
        _, answer = raw.split("</think>", 1)
        return answer.strip()
    # Also strip any stray <think> prefix
    if raw.lstrip().startswith("<think>"):
        raw = raw.lstrip()[len("<think>"):]
    return raw.strip()


def backend_health() -> tuple[bool, bool]:
    """Returns (backend_ok, vl_model_ok)"""
    def _ping(url: str) -> bool:
        try:
            r = requests.get(f"{url}/health", timeout=2)
            return r.status_code == 200
        except Exception:
            return False
    return _ping(BACKEND_URL), _ping(VL_MODEL_URL)


def submit_text_query(stats: dict, prompt: str) -> None:
    """
    Streams response from fast text model (Qwen3.5-35B-A3B, port 8081).
    Uses st.write_stream so tokens appear in real time.
    </think> tokens stripped before display.
    """
    payload = {"stats": stats, "prompt": prompt}
    st.session_state.stream_output = ""

    def _token_gen():
        try:
            with requests.post(
                f"{BACKEND_URL}/analyze/stream",
                json=payload,
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                buffer = ""
                think_done = False
                for chunk in resp.iter_content(chunk_size=None):
                    if chunk:
                        text = chunk.decode("utf-8", errors="ignore")
                        buffer += text
                        # Strip thinking section before first </think>
                        if not think_done:
                            if "</think>" in buffer:
                                _, buffer = buffer.split("</think>", 1)
                                think_done = True
                            else:
                                continue   # accumulate until </think> found
                        yield buffer
                        st.session_state.stream_output += buffer
                        buffer = ""
        except requests.exceptions.ConnectionError:
            yield "\n\n⚠️  Backend offline. Start the FastAPI server first."
        except Exception as e:
            yield f"\n\n⚠️  Error: {e}"

    with st.container():
        st.write_stream(_token_gen())


def submit_vision_query(image_b64: str, prompt: str) -> dict:
    """
    POSTs screenshot to VL model endpoint (Qwen3-VL-32B, port 8080).
    Returns job dict: {job_id, status, result?}
    NOT streamed — VL takes longer, uses job polling pattern.
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/analyze/vision",
            json={"image_b64": image_b64, "prompt": prompt},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()          # {"job_id": "...", "status": "queued"}
    except requests.exceptions.ConnectionError:
        return {"error": "Backend offline."}
    except Exception as e:
        return {"error": str(e)}


def poll_job(job_id: str) -> dict:
    """Poll /job/{id} until done or failed."""
    try:
        resp = requests.get(f"{BACKEND_URL}/job/{job_id}", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def submit_offload_task(task_type: str, description: str, input_data: dict) -> dict:
    """Submit a heavy compute task for cloud offload."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/offload",
            json={"task_type": task_type, "description": description, "input_data": input_data},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Backend offline."}
    except Exception as e:
        return {"error": str(e)}


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        # Logo area
        st.markdown("""
        <div style="padding:16px 0 24px 0;text-align:center">
          <div style="font-family:'Space Grotesk',sans-serif;font-size:26px;font-weight:700;color:#F8FAFC">
            ⚡ LightningBoost
          </div>
          <div style="font-size:12px;color:#64748B;margin-top:4px">
            Hybrid Local-Cloud AI Engine
          </div>
        </div>
        <hr style="margin-bottom:20px">
        """, unsafe_allow_html=True)

        # Connection status
        backend_ok, vl_ok = backend_health()
        def _dot(ok): return "🟢" if ok else "🔴"

        st.markdown(f"""
        <div class="lb-card" style="padding:14px 16px">
          <div style="font-size:12px;color:#94A3B8;font-family:'Space Grotesk',sans-serif;
                      letter-spacing:.05em;text-transform:uppercase;margin-bottom:10px">
            Services
          </div>
          <div style="display:flex;flex-direction:column;gap:8px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:13px;color:#CBD5E1">FastAPI Backend</span>
              <span style="font-size:13px">{_dot(backend_ok)} {'Online' if backend_ok else 'Offline'}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:13px;color:#CBD5E1">VL Model (32B)</span>
              <span style="font-size:13px">{_dot(vl_ok)} {'Ready' if vl_ok else 'Offline'}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:13px;color:#CBD5E1">AMD MI300X</span>
              <span style="font-size:13px">{_dot(backend_ok)} {'Active' if backend_ok else '—'}</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Navigation
        st.markdown("""
        <div style="font-size:11px;color:#64748B;font-family:'Space Grotesk',sans-serif;
                    letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">
          Navigation
        </div>
        """, unsafe_allow_html=True)

        nav = st.radio(
            "",
            ["Monitor", "AI Analysis", "Task Offload", "History", "Settings"],
            label_visibility="collapsed",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Local agent hint
        with st.expander("📡 Local Agent", expanded=False):
            st.markdown("""
            <div style="font-size:12px;color:#94A3B8;line-height:1.6">
              Run <code>local_agent.py</code> on your laptop to push real stats.<br><br>
              <code>python local_agent.py --backend http://YOUR_IP:8000</code>
            </div>
            """, unsafe_allow_html=True)

        # Footer
        st.markdown("""
        <div style="position:absolute;bottom:20px;left:0;right:0;text-align:center;
                    font-size:11px;color:#334155">
          AMD MI300X · Qwen3-VL-32B · ROCm
        </div>
        """, unsafe_allow_html=True)

    return nav


# ── Monitor Tab ───────────────────────────────────────────────────────────────

def render_monitor():
    st.markdown("""
    <h2 style="margin-bottom:4px">System Monitor</h2>
    <p style="color:#64748B;font-size:14px;margin-bottom:24px">
      Enter stats manually or run <code>local_agent.py</code> on your laptop to auto-populate.
    </p>
    """, unsafe_allow_html=True)

    # ── Stats input panel ──
    # NOTE: psutil here reads the HF Space container, not the user's laptop.
    # We intentionally use manual sliders + allow local_agent.py to POST stats.
    with st.expander("📥 Input System Stats", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            ram_pct   = st.slider("RAM Used %",       0, 100,
                                  st.session_state.agent_stats.get("ram_pct", 65))
            cpu_pct   = st.slider("CPU Used %",       0, 100,
                                  st.session_state.agent_stats.get("cpu_pct", 42))
        with col2:
            disk_pct  = st.slider("Disk Used %",      0, 100,
                                  st.session_state.agent_stats.get("disk_pct", 58))
            processes = st.number_input("Running Processes", 1, 1000,
                                        int(st.session_state.agent_stats.get("processes", 120)))
        ram_free_mb = st.number_input(
            "Free RAM (MB)", 0, 32768,
            int(st.session_state.agent_stats.get("ram_free_mb", 2048))
        )

    stats = {
        "ram_pct": ram_pct, "cpu_pct": cpu_pct,
        "disk_pct": disk_pct, "processes": processes,
        "ram_free_mb": ram_free_mb,
    }

    # ── Metric cards ──
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    ram_delta  = f"{ram_pct - 70:+.0f}% vs avg"
    cpu_delta  = f"{cpu_pct - 50:+.0f}% vs avg"
    c1.metric("RAM Usage",   f"{ram_pct:.0f}%",  delta=ram_delta,
              delta_color="inverse")
    c2.metric("CPU Usage",   f"{cpu_pct:.0f}%",  delta=cpu_delta,
              delta_color="inverse")
    c3.metric("Disk Usage",  f"{disk_pct:.0f}%", delta=None)
    c4.metric("Processes",   f"{int(processes)}", delta=None)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ──
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### RAM Timeline")
        # Simulated rolling window — replace with real agent data in production
        sim_ram = [max(0, min(100, ram_pct - 20 + i * 2 + (i % 3) * 3))
                   for i in range(20)]
        times   = pd.date_range(end=pd.Timestamp.now(), periods=20, freq="30s")
        fig_ram = go.Figure()
        fig_ram.add_trace(go.Scatter(
            x=times, y=sim_ram,
            mode="lines",
            fill="tozeroy",
            line=dict(color="#22C55E", width=2),
            fillcolor="rgba(34,197,94,0.08)",
            name="RAM %",
        ))
        fig_ram.add_hline(y=75, line_dash="dot",
                          line_color="#FACC15", annotation_text="Warn 75%",
                          annotation_font_color="#FACC15")
        fig_ram.add_hline(y=90, line_dash="dot",
                          line_color="#F87171", annotation_text="Critical 90%",
                          annotation_font_color="#F87171")
        fig_ram.update_layout(**PLOTLY_DARK, height=260,
                               margin=dict(l=0, r=0, t=10, b=0),
                               showlegend=False,
                               yaxis=PLOTLY_DARK["yaxis"] or {"range": [0, 100]})
        st.plotly_chart(fig_ram, use_container_width=True)

    with col_r:
        st.markdown("#### Task Distribution")
        history = st.session_state.task_history
        status_counts = {"Local": 0, "Cloud": 0, "Pending": 0, "Failed": 0}
        for t in history:
            s = t.get("status", "").lower()
            if s == "completed":
                target = t.get("target", "local").capitalize()
                status_counts[target] = status_counts.get(target, 0) + 1
            elif s in ("pending", "queued"):
                status_counts["Pending"] += 1
            elif s == "failed":
                status_counts["Failed"] += 1

        if sum(status_counts.values()) == 0:
            status_counts = {"Local": 5, "Cloud": 3, "Pending": 1, "Failed": 0}

        fig_pie = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            hole=0.45,
            color_discrete_map={
                "Local": "#22C55E", "Cloud": "#60A5FA",
                "Pending": "#FACC15", "Failed": "#F87171",
            },
        )
        fig_pie.update_traces(textfont_color="#F8FAFC")
        fig_pie.update_layout(**PLOTLY_DARK, height=260,
                               margin=dict(l=0, r=0, t=10, b=0),
                               showlegend=True,
                               legend=dict(font_color="#CBD5E1"))
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Quick AI Tips ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Quick AI Tips")

    col_tip, col_sev = st.columns([4, 1])
    with col_tip:
        # Deterministic rule-based tips (instant, no LLM call needed for basic advice)
        tips = []
        if ram_pct > 85:
            tips.append("🔴 **Critical:** RAM above 85% — offload heavy tasks to cloud immediately.")
        elif ram_pct > 70:
            tips.append("🟡 **Warning:** RAM above 70% — consider closing unused applications.")
        else:
            tips.append("🟢 **Good:** RAM usage is healthy.")

        if cpu_pct > 80:
            tips.append("🔴 **High CPU:** Intensive process detected — ideal for cloud offload.")
        elif cpu_pct > 60:
            tips.append("🟡 **Moderate CPU:** Monitor; schedule heavy tasks to off-peak.")
        else:
            tips.append("🟢 **CPU normal:** Local execution preferred for light tasks.")

        if processes > 200:
            tips.append(f"🟡 **{int(processes)} processes running:** Review startup apps to reduce baseline usage.")

        if ram_free_mb < 500:
            tips.append(f"🔴 **Only {ram_free_mb:.0f} MB free:** Close browser tabs to free ~200 MB each.")

        for tip in tips:
            st.markdown(tip)

    with col_sev:
        severity = "high" if ram_pct > 85 or cpu_pct > 80 else \
                   "medium" if ram_pct > 70 or cpu_pct > 60 else "low"
        st.markdown(
            f'<br><div style="text-align:center">{_severity_badge(severity)}</div>',
            unsafe_allow_html=True,
        )

    return stats


# ── AI Analysis Tab ───────────────────────────────────────────────────────────

def render_ai_analysis(stats: dict):
    st.markdown("""
    <h2 style="margin-bottom:4px">AI Analysis</h2>
    <p style="color:#64748B;font-size:14px;margin-bottom:24px">
      Text queries → Qwen3.5-35B-A3B (fast) &nbsp;|&nbsp;
      Screenshot → Qwen3-VL-32B (vision)
    </p>
    """, unsafe_allow_html=True)

    tab_text, tab_vision = st.tabs(["💬 Text Query", "📸 Screenshot Analysis"])

    # ── Text Query Tab ──
    with tab_text:
        st.markdown("""
        <div class="lb-card lb-card-accent">
          <div style="font-size:13px;color:#94A3B8">
            Current stats passed automatically: RAM <strong style="color:#22C55E">{ram}%</strong>
            · CPU <strong style="color:#22C55E">{cpu}%</strong>
            · Free RAM <strong style="color:#22C55E">{free} MB</strong>
          </div>
        </div>
        """.format(
            ram=stats["ram_pct"], cpu=stats["cpu_pct"],
            free=int(stats["ram_free_mb"])
        ), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        preset_col, _ = st.columns([3, 1])
        with preset_col:
            preset = st.selectbox("Quick prompts (or type custom below)", [
                "Custom prompt…",
                "Give me 5 specific tips to free up RAM on my laptop right now.",
                "Which of my running processes should I close first?",
                "Should I run this video export locally or offload to cloud?",
                "Explain why my CPU is spiking and what I should do.",
                "What startup apps can I safely disable to improve boot time?",
            ])

        if preset == "Custom prompt…":
            user_prompt = st.text_area(
                "Your question",
                placeholder="e.g. Why is my laptop so slow with only 2GB RAM left?",
                height=100,
            )
        else:
            user_prompt = preset
            st.markdown(
                f'<div class="lb-card" style="font-size:13px;color:#CBD5E1;padding:12px 16px">'
                f'{user_prompt}</div>',
                unsafe_allow_html=True,
            )

        ask_col, clear_col = st.columns([2, 1])
        with ask_col:
            ask_btn = st.button("Ask AI (Streaming)", use_container_width=True,
                                disabled=not user_prompt)
        with clear_col:
            st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
            clear_btn = st.button("Clear", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if clear_btn:
            st.session_state.last_tips = ""
            st.rerun()

        if ask_btn and user_prompt:
            st.markdown("---")
            st.markdown(
                '<div style="font-size:12px;color:#64748B;margin-bottom:8px">'
                'Qwen3.5-35B-A3B · thinking tokens stripped · streaming</div>',
                unsafe_allow_html=True,
            )
            submit_text_query(stats, user_prompt)

    # ── Vision / Screenshot Tab ──
    with tab_vision:
        st.markdown("""
        <div class="lb-card lb-card-accent">
          <strong style="color:#F8FAFC">How it works</strong>
          <div style="font-size:13px;color:#94A3B8;margin-top:6px;line-height:1.6">
            Upload a screenshot of your Task Manager (Windows), Activity Monitor (Mac),
            or <code>htop</code> output. Qwen3-VL-32B on AMD MI300X will visually
            analyze the processes and give targeted advice.
          </div>
        </div>
        """, unsafe_allow_html=True)

        img_file = st.file_uploader(
            "Drop screenshot here (PNG / JPG)",
            type=["png", "jpg", "jpeg"],
            help="Task Manager · Activity Monitor · htop · Any resource view",
        )

        vision_prompt = st.text_area(
            "What to analyze (optional — leave blank for auto)",
            value="Analyze this system screenshot. Identify the top memory and CPU hogs. "
                  "Give 5 specific, actionable recommendations to free up resources.",
            height=90,
        )

        if img_file:
            st.markdown("<br>", unsafe_allow_html=True)
            prev_col, _ = st.columns([1, 2])
            with prev_col:
                st.image(img_file, caption="Your screenshot", use_container_width=True)

            analyze_btn = st.button(
                "Analyze with Qwen3-VL-32B",
                use_container_width=True,
                type="primary",
            )

            if analyze_btn:
                img_b64 = base64.b64encode(img_file.getvalue()).decode()

                with st.spinner("Submitting to VL model…"):
                    job = submit_vision_query(img_b64, vision_prompt)

                if "error" in job:
                    st.error(f"Submission failed: {job['error']}")
                else:
                    job_id = job.get("job_id", 0)
                    st.session_state.vl_job_id = job_id
                    st.info(f"Job queued — ID: `{job_id[:8] if job_id else 'N/A'}…`")

                    # ── Polling loop (replaces fire-and-forget anti-pattern) ──
                    progress_bar  = st.progress(0)
                    status_text   = st.empty()
                    result_area   = st.empty()
                    elapsed       = 0
                    poll_interval = 2   # seconds
                    timeout       = 120  # max wait

                    while elapsed < timeout:
                        data = poll_job(job_id)
                        status = data.get("status", "unknown")
                        pct = min(95, int(elapsed / timeout * 100))

                        status_text.markdown(
                            f'<div style="font-size:12px;color:#64748B">'
                            f'Status: {_status_badge(status)} · {elapsed}s elapsed</div>',
                            unsafe_allow_html=True,
                        )
                        progress_bar.progress(pct)

                        if status == "completed":
                            progress_bar.progress(100)
                            raw_result = data.get("result", "")
                            clean      = strip_qwen_thinking(raw_result)
                            result_area.markdown(
                                f'<div class="lb-card lb-card-accent">'
                                f'<div style="font-size:12px;color:#64748B;margin-bottom:8px">'
                                f'Qwen3-VL-32B · Vision Analysis</div>'
                                f'{clean}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                            # Add to history
                            st.session_state.task_history.insert(0, {
                                "id":          job_id,
                                "type":        "Vision Analysis",
                                "description": "Screenshot upload",
                                "status":      "completed",
                                "target":      "Cloud",
                                "created":     datetime.now(),
                            })
                            break

                        elif status in ("failed", "error"):
                            progress_bar.empty()
                            result_area.error(
                                f"VL job failed: {data.get('error', 'unknown error')}"
                            )
                            break

                        time.sleep(poll_interval)
                        elapsed += poll_interval

                    else:
                        st.warning("Job timed out after 120s. Check backend logs.")

        else:
            st.markdown("""
            <div style="text-align:center;padding:48px 0;color:#334155">
              <div style="font-size:48px">📸</div>
              <div style="font-size:14px;margin-top:8px">Upload a screenshot to begin vision analysis</div>
            </div>
            """, unsafe_allow_html=True)


# ── Task Offload Tab ──────────────────────────────────────────────────────────

def render_task_offload(stats: dict):
    st.markdown("""
    <h2 style="margin-bottom:4px">Task Offload</h2>
    <p style="color:#64748B;font-size:14px;margin-bottom:24px">
      Submit compute-heavy jobs to AMD MI300X cloud GPU.
    </p>
    """, unsafe_allow_html=True)

    # Smart routing hint
    threshold_note = "cloud" if stats.get("ram_pct", 0) > 70 else "local"
    st.markdown(
        f'<div class="lb-card lb-card-accent" style="font-size:13px;color:#94A3B8">'
        f'Based on current RAM ({stats.get("ram_pct",0):.0f}%) — '
        f'<strong style="color:#22C55E">recommended: {threshold_note} execution</strong>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    task_type = st.selectbox(
        "Task Type",
        ["TEXT_GENERATION", "IMAGE_CLASSIFICATION", "VIDEO_RENDER",
         "EMBEDDING", "CODE_EXECUTION", "LIGHTWEIGHT"],
        help="Determines which cloud endpoint processes the job"
    )

    description = st.text_input(
        "Task Description",
        placeholder="Brief description of what this task should do",
    )

    # ── Dynamic input fields per task type ──
    input_data = {}

    if task_type == "TEXT_GENERATION":
        col_a, col_b = st.columns([3, 1])
        with col_a:
            prompt = st.text_area("Prompt", height=120,
                                  placeholder="Enter your generation prompt…")
        with col_b:
            max_tokens = st.slider("Max tokens", 64, 4096, 512, step=64)
            temperature = st.slider("Temperature", 0.0, 1.0, 0.6, step=0.05)
        input_data = {"prompt": prompt, "max_tokens": max_tokens,
                      "temperature": temperature}

    elif task_type == "IMAGE_CLASSIFICATION":
        image_url = st.text_input("Image URL", placeholder="https://…")
        input_data = {"image_url": image_url}

    elif task_type == "VIDEO_RENDER":
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            source = st.text_input("Source file path or URL")
            resolution = st.selectbox("Output resolution", ["1080p", "720p", "4K", "480p"])
        with col_v2:
            codec = st.selectbox("Codec", ["H.264", "H.265", "AV1", "VP9"])
            bitrate = st.slider("Bitrate (Mbps)", 1, 50, 8)
        input_data = {"source": source, "resolution": resolution,
                      "codec": codec, "bitrate_mbps": bitrate}

    elif task_type == "EMBEDDING":
        text = st.text_area("Text to embed", height=100,
                            placeholder="Paste document or query text…")
        input_data = {"text": text}

    elif task_type == "CODE_EXECUTION":
        code = st.text_area("Python code to run on GPU node", height=150,
                            placeholder="import torch\n…")
        timeout_s = st.slider("Timeout (seconds)", 10, 300, 60)
        input_data = {"code": code, "timeout_seconds": timeout_s}

    st.markdown("<br>", unsafe_allow_html=True)
    submit_btn = st.button("🚀 Submit to Cloud GPU", use_container_width=True,
                            disabled=not description)

    if submit_btn and description:
        with st.spinner("Submitting task…"):
            result = submit_offload_task(task_type, description, input_data)

        if "error" in result:
            st.error(f"Submission failed: {result['error']}")
        else:
            task_id = result.get("task_id", "N/A")
            st.success(f"Task queued — ID: `{task_id[:8] if task_id != 'N/A' else 'N/A'}…`")
            st.markdown(
                f'<div class="lb-card" style="font-size:13px;color:#94A3B8">'
                f'Estimated compute time: <strong style="color:#F8FAFC">'
                f'{result.get("estimated_seconds", "calculating…")}s</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.session_state.task_history.insert(0, {
                "id":          task_id,
                "type":        task_type,
                "description": description,
                "status":      result.get("status", "queued"),
                "target":      "Cloud",
                "created":     datetime.now(),
            })

    elif submit_btn:
        st.warning("Please fill in the Task Description.")


# ── History Tab ───────────────────────────────────────────────────────────────

def render_history():
    st.markdown("""
    <h2 style="margin-bottom:4px">Task History</h2>
    <p style="color:#64748B;font-size:14px;margin-bottom:24px">
      All submitted tasks this session.
    </p>
    """, unsafe_allow_html=True)

    col_ref, col_clear = st.columns([5, 1])
    with col_ref:
        if st.session_state.active_job_id:
            if st.button("🔄 Refresh Active Job"):
                job = poll_job(st.session_state.active_job_id)
                for t in st.session_state.task_history:
                    if t.get("id") == st.session_state.active_job_id:
                        t["status"] = job.get("status", t["status"])
                st.rerun()

    with col_clear:
        st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
        if st.button("Clear All"):
            st.session_state.task_history = []
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if not st.session_state.task_history:
        st.markdown("""
        <div style="text-align:center;padding:64px 0;color:#334155">
          <div style="font-size:48px">📋</div>
          <div style="font-size:14px;margin-top:8px">No tasks yet — submit one from Task Offload or AI Analysis</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Stats row ──
    total     = len(st.session_state.task_history)
    completed = sum(1 for t in st.session_state.task_history if t["status"] == "completed")
    pending   = sum(1 for t in st.session_state.task_history
                    if t["status"] in ("pending", "queued"))
    failed    = sum(1 for t in st.session_state.task_history if t["status"] == "failed")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Tasks",    total)
    m2.metric("Completed",      completed)
    m3.metric("Pending/Queued", pending)
    m4.metric("Failed",         failed)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Table ──
    for task in st.session_state.task_history:
        created_str = (task["created"].strftime("%H:%M:%S")
                       if isinstance(task["created"], datetime)
                       else str(task["created"]))
        target_badge = (_badge("Cloud", "blue")
                        if task.get("target") == "Cloud"
                        else _badge("Local", "green"))

        st.markdown(f"""
        <div class="lb-card" style="display:flex;align-items:center;justify-content:space-between;
                                     flex-wrap:wrap;gap:8px">
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:200px">
            <div style="font-size:14px;font-weight:600;color:#F8FAFC">{task['description'][:60]}</div>
            <div style="font-size:12px;color:#64748B">
              {task['type']} &nbsp;·&nbsp; {created_str}
              &nbsp;·&nbsp; ID: <code style="color:#94A3B8">{str(task['id'])[:8]}…</code>
            </div>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            {target_badge}
            {_status_badge(task['status'])}
          </div>
        </div>
        """, unsafe_allow_html=True)


# ── Settings Tab ─────────────────────────────────────────────────────────────

def render_settings():
    st.markdown("""
    <h2 style="margin-bottom:4px">Settings</h2>
    <p style="color:#64748B;font-size:14px;margin-bottom:24px">
      All URLs read from environment variables. Set them in your HuggingFace Space secrets.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("#### Backend URLs")
    st.markdown("""
    <div class="lb-card" style="font-family:monospace;font-size:13px;color:#94A3B8;line-height:2">
      <div><span style="color:#64748B">AMD_BACKEND_URL</span>
           &nbsp;=&nbsp; <span style="color:#22C55E">{b}</span></div>
      <div><span style="color:#64748B">VL_MODEL_URL</span>
           &nbsp;&nbsp;&nbsp;&nbsp;=&nbsp; <span style="color:#22C55E">{v}</span></div>
      <div><span style="color:#64748B">TEXT_MODEL_URL</span>
           &nbsp;&nbsp;=&nbsp; <span style="color:#22C55E">{t}</span></div>
    </div>
    """.format(b=BACKEND_URL, v=VL_MODEL_URL, t=TEXT_MODEL_URL),
    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### Model Config")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="lb-card">
          <div style="font-size:12px;color:#64748B;margin-bottom:6px">VISION MODEL</div>
          <div style="font-weight:600;color:#F8FAFC">Qwen3-VL-32B-Instruct</div>
          <div style="font-size:12px;color:#94A3B8;margin-top:4px">
            ~19 GB VRAM · Image + Text · Port 8080
          </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="lb-card">
          <div style="font-size:12px;color:#64748B;margin-bottom:6px">FAST TEXT MODEL</div>
          <div style="font-weight:600;color:#F8FAFC">Qwen3.5-35B-A3B</div>
          <div style="font-size:12px;color:#94A3B8;margin-top:4px">
            ~20 GB VRAM · Text only · MoE 3B active · Port 8081
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Connection Test")
    if st.button("Run Connection Test", use_container_width=True):
        with st.spinner("Testing all endpoints…"):
            backend_ok, vl_ok = backend_health()
            time.sleep(0.5)

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            if backend_ok:
                st.success("FastAPI backend: Online")
            else:
                st.error("FastAPI backend: Offline — check AMD droplet is running")
        with res_col2:
            if vl_ok:
                st.success("VL Model (8080): Online")
            else:
                st.error("VL Model (8080): Offline — run llama.cpp server")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Local Agent")
    st.markdown("""
    <div class="lb-card">
      <div style="font-size:13px;color:#94A3B8;line-height:1.8">
        Run <code>local_agent.py</code> on your laptop (not this server) to auto-push real RAM/CPU stats:
      </div>
      <pre style="background:#0F172A;padding:12px;border-radius:8px;
                  font-size:12px;color:#22C55E;margin-top:10px;overflow-x:auto">
pip install psutil requests
python local_agent.py --backend http://YOUR_AMD_DROPLET_IP:8000 --interval 3</pre>
    </div>
    """, unsafe_allow_html=True)


# ── Main App ──────────────────────────────────────────────────────────────────

def main():
    nav = render_sidebar()

    # Persistent stats (shared between monitor and other tabs)
    if nav == "Monitor":
        live_stats = render_monitor()
        # Cache stats for use in other tabs this session
        if live_stats:
            st.session_state.agent_stats = live_stats

    elif nav == "AI Analysis":
        # Use last known stats if available
        cached = st.session_state.agent_stats or {
            "ram_pct": 65, "cpu_pct": 42, "disk_pct": 58,
            "processes": 120, "ram_free_mb": 2048,
        }
        render_ai_analysis(cached)

    elif nav == "Task Offload":
        cached = st.session_state.agent_stats or {
            "ram_pct": 65, "cpu_pct": 42, "disk_pct": 58,
            "processes": 120, "ram_free_mb": 2048,
        }
        render_task_offload(cached)

    elif nav == "History":
        render_history()

    elif nav == "Settings":
        render_settings()


if __name__ == "__main__":
    main()