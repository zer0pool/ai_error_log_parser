from typing import Dict, Any
from app.application.usecase.analyze_log_state import AnalyzeLogState
from app.domain.service.regex_classifier import RegexClassifier
from app.domain.service.log_cleaner import LogCleaner
from app.domain.repository.job_metadata_repository import JobMetadataRepository
from app.domain.repository.vector_store import VectorStore

class AnalysisNodes:
    def __init__(
        self, 
        regex_classifier: RegexClassifier,
        metadata_repo: JobMetadataRepository,
        vector_store: VectorStore
    ):
        self.regex = regex_classifier
        self.metadata_repo = metadata_repo
        self.vector_store = vector_store

    def classify_regex(self, state: AnalyzeLogState) -> Dict[str, Any]:
        category = self.regex.classify(state['trace_log'])
        return {"regex_category": category}

    def fetch_job_metadata(self, state: AnalyzeLogState) -> Dict[str, Any]:
        meta = self.metadata_repo.get_by_id(state['job_id'])
        return {"job_metadata": meta}

    def retrieve_docs(self, state: AnalyzeLogState) -> Dict[str, Any]:
        # Clean log first to improve semantic search match
        cleaned = LogCleaner.clean(state['trace_log'])
        # Search for top 3 similar entries
        docs = self.vector_store.search(cleaned, k=3)
        doc_contents = [d.get('content', '') for d in docs]
        return {"retrieved_docs": doc_contents}
