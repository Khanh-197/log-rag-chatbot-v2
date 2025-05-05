import streamlit as st
import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import get_rag_pipeline

st.set_page_config(
    page_title="Log Analysis RAG Chatbot",
    page_icon="📊",
    layout="wide"
)

# Initialize the RAG pipeline
@st.cache_resource
def init_rag():
    return get_rag_pipeline()

rag_pipeline = init_rag()

# Title and description
st.title("📊 Log Analysis RAG Chatbot")
st.markdown("""
This application allows you to query logs using natural language. 
Ask questions about transactions, errors, or any specific log patterns.
""")

# Query input
query = st.text_input("Enter your query:", placeholder="Example: kiểm tra cho tôi giao dịch có transid ABC-123")

# Query examples
st.markdown("### Example queries:")
examples = [
    "Kiểm tra cho tôi giao dịch có transid ABC-123",
    "Có lỗi nào xảy ra trong hệ thống topup trong 6 giờ qua không?",
    "Tìm các giao dịch thất bại hôm nay",
    "Hiển thị log từ module payment trong 2 giờ qua"
]

def set_example(example):
    st.session_state.query = example

col1, col2 = st.columns(2)
with col1:
    st.button(examples[0], on_click=set_example, args=(examples[0],), use_container_width=True)
    st.button(examples[2], on_click=set_example, args=(examples[2],), use_container_width=True)
with col2:
    st.button(examples[1], on_click=set_example, args=(examples[1],), use_container_width=True)
    st.button(examples[3], on_click=set_example, args=(examples[3],), use_container_width=True)

# Process query
if query:
    with st.spinner("Analyzing logs..."):
        result = rag_pipeline.process_query(query)
    
    # Display AI analysis
    st.markdown("### Analysis")
    st.write(result["analysis"])
    
    # Display relevant logs
    st.markdown("### Relevant Logs")
    
    if result["logs"]:
        # Flatten and clean up logs for display
        logs_for_display = []
        for log in result["logs"]:
            flat_log = {}
            
            # Priority fields to show first
            priority_fields = ["@timestamp", "transid", "message", "level", "service"]
            
            # Add priority fields first
            for field in priority_fields:
                if field in log:
                    # Format timestamp
                    if field == "@timestamp" and isinstance(log[field], str):
                        try:
                            dt = datetime.fromisoformat(log[field].replace('Z', '+00:00'))
                            flat_log[field] = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            flat_log[field] = log[field]
                    else:
                        flat_log[field] = log[field]
            
            # Add remaining fields
            for key, value in log.items():
                if key not in priority_fields:
                    flat_log[key] = value
            
            logs_for_display.append(flat_log)
        
        # Convert to DataFrame for display
        try:
            # Use common columns across all logs
            common_columns = set.intersection(*[set(log.keys()) for log in logs_for_display])
            common_columns = list(common_columns)
            
            # Prioritize certain columns if they exist
            for col in reversed(["message", "transid", "@timestamp"]):
                if col in common_columns:
                    common_columns.remove(col)
                    common_columns.insert(0, col)
            
            df = pd.DataFrame(logs_for_display)[common_columns]
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error displaying logs as table: {e}")
            # Fallback to JSON display
            st.json(logs_for_display)
    else:
        st.info("No relevant logs found for your query.")
    
    # Option to view raw logs
    with st.expander("View Raw Logs"):
        st.json(result["logs"])

# System status and info
with st.sidebar:
    st.subheader("System Information")
    
    # Refresh logs button
    if st.button("Refresh Logs Cache"):
        with st.spinner("Refreshing logs..."):
            logs_count = rag_pipeline.refresh_logs()
            st.success(f"Refreshed {logs_count} logs")
    
    # System status
    st.markdown("**Status**: 🟢 Online")
    
    # Add time ranges for quick queries
    st.subheader("Quick Time Ranges")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Last Hour"):
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            query = f"Show logs from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}"
            st.session_state.query = query
    with col2:
        if st.button("Last 24 Hours"):
            query = "Show logs from the last 24 hours"
            st.session_state.query = query

    # Add filters for common log properties
    st.subheader("Log Filters")
    
    service = st.selectbox(
        "Service",
        ["All", "payment", "topup", "wallet", "auth"],
        index=0
    )
    
    level = st.selectbox(
        "Log Level",
        ["All", "ERROR", "WARN", "INFO", "DEBUG"],
        index=0
    )
    
    if st.button("Apply Filters"):
        filter_query = "Show"
        
        if level != "All":
            filter_query += f" {level.lower()}"
        
        filter_query += " logs"
        
        if service != "All":
            filter_query += f" from {service} service"
        
        st.session_state.query = filter_query
