# System Guide: AI-Powered Airflow Log Analysis Service

This document provides a comprehensive overview of the project architecture, directory structure, and operational guidelines for developers and AI agents.

## 1. Project Overview
This service automates the analysis of Airflow execution failures using **RAG (Retrieval-Augmented Generation)** and **Agentic Workflows**. It classifies error logs, identifies root causes, and provides resolution guides by synthesizing domain knowledge and historical data.

### Key Technologies
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **Framework**: FastAPI (DDD Pattern)
- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph)
- **Vector DB**: FAISS
- **LLM**: Google Gemini 1.5 (Accessible via `langchain-google-genai`)
- **Dashboard**: Streamlit

---

## 2. Architecture & Directory Structure
The project follows **Domain-Driven Design (DDD)** principles to separate business logic from technical infrastructure.

### `/app` - Core Application (DDD Layers)
- **`domain/`**: The heart of the system.
    - `entity/`: Pydantic models (e.g., `AnalysisResult`) representing business concepts.
    - `repository/`: Abstract interfaces (ABCs) for data access (e.g., `VectorStore`).
    - `service/`: Pure business logic like `RegexClassifier` and `LogCleaner`.
- **`application/`**: Orchestration and Use Cases.
    - `usecase/`: Main entry points for business processes. `analyze_log.py` contains the graph assembly logic.
    - `nodes/`: Logic for individual steps in the LangGraph workflow.
- **`infrastructure/`**: Technical implementations of domain interfaces.
    - `vector_db/`: FAISS implementation for semantic search.
    - `llm/`: Integration with Gemini API for reasoning.
    - `job_meta/`: Data retrieval for job-specific context (e.g., owner, job type).
- **`controller/`**: Exposure to the external world.
    - `router/`: FastAPI endpoints.
    - `schemas/`: Input/Output DTOs (Data Transfer Objects).
    - `factory/`: Dependency Injection (DI) logic to assemble the layers.

### Support Directories
- **`admin/`**: Streamlit dashboard for observability and human-in-the-loop labeling.
- **`scripts/`**: Automations for log batch processing (`batch_process.py`) and Vector DB indexing (`index_knowledge.py`).
- **`data/`**: Storage for raw logs, processed patterns, and FAISS index files.
- **`docs/`**: Domain-specific knowledge documents used by the RAG system.

---

## 3. Core Data Flow
1. **Ingestion**: A log trace and job ID are sent to `/api/v1/analyze`.
2. **Preprocessing**: The log is cleaned (Dynamic IDs/Timestamps removed) to identify its pattern.
3. **Graph Execution (LangGraph)**:
    - **Classify Node**: Quick classification using Regex patterns.
    - **Context Node**: Fetches metadata about the job (e.g., SQL vs. Notebook).
    - **RAG Node**: Retrieves top-N similar historical cases and domain knowledge from FAISS.
    - **Verify Node**: The LLM synthesizes everything to generate a final, high-confidence report.
4. **Response**: Final analysis and resolution guide are returned to the user.

---

## 4. Operation Instructions

### Initialization
```bash
# Install dependencies
make install

# Process 56k logs and initialize Vector DB
make setup-data
```

### Execution
- **Start API**: `make run-api` (Port 8000)
- **Start Admin**: `make run-admin` (Port 8501)

### Adding New Knowledge
1. Update `docs/domain_knowledge.md` and run `make setup-data`.
2. **OR** use the "Manual Labeling" tab in the Streamlit Admin dashboard to add entries directly to the FAISS index.

---

## 5. Notes for AI Agents
- **Environment**: Use `uv run <script>` to ensure the correct virtual environment is used.
- **Modularity**: To swap the LLM, implement a new engine in `app/infrastructure/llm` and update the `factory`.
- **Tracing**: LangSmith is configured in `.env` for deep debugging of the LangGraph workflow.
