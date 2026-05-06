"""
Frontend Streamlit application for LightningBoost
Displays system metrics, recommendations, and task submission
"""
import streamlit as st
import sys
import os
import time
import asyncio
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.client import CloudClient, VLLMClient
from shared.models import Task, SystemMetrics
from shared.config import TaskType, CLOUD_BASE_URL, VLLM_BASE_URL
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Page config
st.set_page_config(
    page_title="LightningBoost Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize clients
cloud_client = CloudClient(CLOUD_BASE_URL)
vllm_client = VLLMClient(VLLM_BASE_URL)

# Session state
if "task_history" not in st.session_state:
    st.session_state.task_history = []
if "metrics_history" not in st.session_state:
    st.session_state.metrics_history = []


def main():
    """Main Streamlit app"""
    
    # Header
    st.markdown("# ⚡ LightningBoost Dashboard")
    st.markdown("*AI-powered task router for hybrid local-cloud execution*")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        cloud_status = cloud_client.get_health()
        vllm_status = vllm_client.health_check()
        
        st.markdown(f"**Cloud Backend:** {'✅ Connected' if cloud_status else '❌ Offline'}")
        st.markdown(f"**vLLM Endpoint:** {'✅ Connected' if vllm_status else '❌ Offline'}")
        
        tab_mode = st.radio(
            "Dashboard Mode",
            ["Monitor", "Task Submission", "Task History", "Settings"]
        )
    
    # Main content based on mode
    if tab_mode == "Monitor":
        show_monitor_view()
    elif tab_mode == "Task Submission":
        show_task_submission()
    elif tab_mode == "Task History":
        show_task_history()
    else:
        show_settings()


def show_monitor_view():
    """System monitoring dashboard"""
    st.markdown("## 📊 System Monitoring")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.spinner("Loading metrics..."):
            # Simulated system metrics (would come from local_agent in production)
            ram_percent = 65.0
            st.metric("RAM Usage", f"{ram_percent:.1f}%", delta="-5%")
    
    with col2:
        cpu_percent = 42.0
        st.metric("CPU Usage", f"{cpu_percent:.1f}%", delta="+2%")
    
    with col3:
        disk_percent = 58.0
        st.metric("Disk Usage", f"{disk_percent:.1f}%", delta="0%")
    
    with col4:
        processes = 156
        st.metric("Processes", f"{processes}", delta="+3")
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("### Memory Timeline")
        # Simulated data
        times = pd.date_range(start='2024-01-01', periods=20, freq='H')
        memory_data = pd.DataFrame({
            'timestamp': times,
            'ram_percent': [50 + i*1.5 + (i%3)*2 for i in range(20)]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=memory_data['timestamp'],
            y=memory_data['ram_percent'],
            mode='lines+markers',
            name='RAM %',
            line=dict(color='#FF6B6B')
        ))
        fig.update_layout(height=300, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.markdown("### Task Distribution")
        task_data = {
            'Local': 12,
            'Cloud': 8,
            'Pending': 3
        }
        fig = px.pie(
            values=list(task_data.values()),
            names=list(task_data.keys()),
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Recommendations
    st.markdown("### 💡 AI Recommendations")
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("""
            ✅ **System is running smoothly!**
            
            - Close 2-3 Chrome tabs to free 200MB
            - Consider moving heavy tasks to cloud when RAM > 75%
            - Disable auto-startup apps to improve boot time
            """)
        with col2:
            severity = "low"
            color_map = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            st.markdown(f"{color_map[severity]} Severity: {severity.upper()}")


def show_task_submission():
    """Task submission interface"""
    st.markdown("## 📋 Submit Task")
    
    with st.form("task_form"):
        task_type = st.selectbox(
            "Task Type",
            ["TEXT_GENERATION", "IMAGE_CLASSIFICATION", "EMBEDDING", "LIGHTWEIGHT"]
        )
        
        description = st.text_input("Task Description", placeholder="What should this task do?")
        
        if task_type == "TEXT_GENERATION":
            prompt = st.text_area("Prompt", placeholder="Enter your prompt here", height=150)
            max_tokens = st.slider("Max Tokens", 10, 2000, 256)
            input_data = {"prompt": prompt, "max_tokens": max_tokens}
        
        elif task_type == "IMAGE_CLASSIFICATION":
            image_url = st.text_input("Image URL", placeholder="https://...")
            input_data = {"image_url": image_url}
        
        elif task_type == "EMBEDDING":
            text = st.text_area("Text to Embed", placeholder="Enter text...", height=100)
            input_data = {"text": text}
        
        else:
            input_data = {}
        
        submitted = st.form_submit_button("🚀 Submit Task", use_container_width=True)
        
        if submitted and description:
            with st.spinner("Submitting task..."):
                try:
                    task_data = {
                        "task_type": task_type,
                        "description": description,
                        "input_data": input_data
                    }
                    
                    result = cloud_client.submit_task(task_data)
                    
                    st.success(f"✅ Task submitted! ID: {result['task_id'][:8]}")
                    st.session_state.task_history.insert(0, {
                        "id": result['task_id'],
                        "type": task_type,
                        "description": description,
                        "status": result['status'],
                        "created": datetime.now()
                    })
                
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        elif submitted:
            st.warning("Please fill in all fields")


def show_task_history():
    """Task history view"""
    st.markdown("## 📜 Task History")
    
    if st.session_state.task_history:
        df = pd.DataFrame(st.session_state.task_history)
        df['created'] = pd.to_datetime(df['created']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Status color coding
        status_colors = {
            'pending': '🟡',
            'running': '🔵',
            'completed': '🟢',
            'failed': '🔴',
            'queued_cloud': '⚙️'
        }
        df['status'] = df['status'].apply(lambda x: f"{status_colors.get(x, '•')} {x}")
        
        st.dataframe(
            df[['created', 'type', 'description', 'status']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No tasks yet. Submit one above!")


def show_settings():
    """Settings view"""
    st.markdown("## ⚙️ Settings")
    
    st.markdown("### Cloud Configuration")
    cloud_url = st.text_input("Cloud Backend URL", value=CLOUD_BASE_URL)
    
    st.markdown("### vLLM Configuration")
    vllm_url = st.text_input("vLLM Endpoint URL", value=VLLM_BASE_URL)
    
    st.markdown("### Monitoring")
    refresh_interval = st.slider("Refresh Interval (seconds)", 1, 60, 5)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Settings"):
            st.success("Settings saved!")
    with col2:
        if st.button("🔄 Test Connection"):
            with st.spinner("Testing..."):
                cloud_ok = cloud_client.get_health()
                vllm_ok = vllm_client.health_check()
                
                st.markdown(f"**Cloud:** {'✅' if cloud_ok else '❌'}")
                st.markdown(f"**vLLM:** {'✅' if vllm_ok else '❌'}")


if __name__ == "__main__":
    main()
