.PHONY: install sync add lock export setup-data run-api run-admin clean help

# Variables
UV := uv
RUN := $(UV) run

help:
	@echo ""
	@echo "  [uv package management]"
	@echo "  make install      Install/sync all dependencies from uv.lock"
	@echo "  make lock         Regenerate uv.lock from pyproject.toml"
	@echo "  make add pkg=...  Add a new package  (e.g. make add pkg=httpx)"
	@echo "  make export       Export uv.lock -> requirements.txt (for pip/Docker)"
	@echo ""
	@echo "  [data setup]"
	@echo "  make setup-data   Run log preprocessing and Vector DB indexing"
	@echo ""
	@echo "  [run]"
	@echo "  make run-api      Start FastAPI server (port 8000)"
	@echo "  make run-admin    Start Streamlit dashboard (port 8501)"
	@echo ""
	@echo "  [cleanup]"
	@echo "  make clean        Remove .venv and __pycache__"
	@echo ""

# ── uv ─────────────────────────────────────────────────────────────────────
install:
	$(UV) sync
	@echo "Dependencies synced."

lock:
	$(UV) lock
	@echo "uv.lock regenerated."

add:
	@if [ -z "$(pkg)" ]; then echo "Usage: make add pkg=<package>"; exit 1; fi
	$(UV) add $(pkg)

export:
	$(UV) export --no-dev -o requirements.txt
	@echo "requirements.txt generated from uv.lock."

# ── data ───────────────────────────────────────────────────────────────────
setup-data:
	@echo "Processing logs..."
	$(RUN) scripts/batch_process.py
	@echo "Indexing knowledge base..."
	$(RUN) scripts/index_knowledge.py

# ── run ────────────────────────────────────────────────────────────────────
run-api:
	$(RUN) uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

run-admin:
	$(RUN) streamlit run admin/dashboard.py

# ── cleanup ────────────────────────────────────────────────────────────────
clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleaned up."
