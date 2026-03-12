import streamlit as st
import pandas as pd
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.infrastructure.vector_db.faiss_store import FaissVectorStore
from app.domain.service.log_cleaner import LogCleaner

st.set_page_config(page_title="Airflow AI Log Analyzer Admin", layout="wide")

st.title("👨‍🔧 Airflow AI Log Analyzer Admin")

# Sidebar for configuration
st.sidebar.header("Configuration")
index_path = st.sidebar.text_input("Index Path", "data/vector_index.bin")
metadata_path = st.sidebar.text_input("Metadata Path", "data/metadata.pkl")

# Initialize Vector DB
@st.cache_resource
def get_vector_db():
    vdb = FaissVectorStore()
    vdb.load(index_path, metadata_path)
    return vdb

vdb = get_vector_db()

tabs = st.tabs(["Dashboard", "Knowledge Base Search", "Manual Labeling"])

with tabs[0]:
    st.header("Overview")
    if vdb.index:
        st.metric("Total Indexed Chunks", len(vdb.metadata))
        
        # Mock statistics
        st.subheader("Classification Accuracy Trend")
        chart_data = pd.DataFrame({
            'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'Accuracy': [0.65, 0.72, 0.78, 0.81, 0.85, 0.84, 0.88]
        })
        st.line_chart(chart_data.set_index('Day'))
    else:
        st.warning("Vector index not loaded. Please check the paths.")

with tabs[1]:
    st.header("Search Knowledge Base")
    query = st.text_input("Enter log or keyword to search")
    if query:
        results = vdb.search(query, k=5)
        for i, res in enumerate(results):
            with st.expander(f"Result {i+1} (Score: {1 - res['distance']:.4f})"):
                st.write(f"**Source:** {res.get('source', 'Unknown')}")
                st.code(res.get('content', ''))

with tabs[2]:
    st.header("Add New Knowledge (Manual Labeling)")
    with st.form("label_form"):
        new_log = st.text_area("Log Pattern / Trace Log")
        new_guide = st.text_area("Correct Resolution Guide")
        category = st.selectbox("Category", ["SENSOR_TIMEOUT", "BQ_SCHEMA_MISMATCH", "BQ_AUTH_ERROR", "GKE_OOM", "OTHER"])
        submit = st.form_submit_button("Add to Knowledge Base")
        
        if submit:
            if new_log and new_guide:
                cleaned_log = LogCleaner.clean(new_log)
                vdb.add_texts([cleaned_log], [{"source": "manual_label", "content": new_guide, "category": category}])
                vdb.save(index_path, metadata_path)
                st.success("New knowledge added and re-indexed!")
            else:
                st.error("Please provide both log and guide.")
