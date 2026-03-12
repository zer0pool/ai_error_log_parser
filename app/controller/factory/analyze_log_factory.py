import os
from app.application.usecase.analyze_log import AnalyzeLogUseCase
from app.application.nodes.analysis_nodes import AnalysisNodes
from app.domain.service.regex_classifier import RegexClassifier
from app.infrastructure.job_meta.http_gateway import HttpJobMetadataGateway
from app.infrastructure.vector_db.faiss_store import FaissVectorStore
from app.infrastructure.llm.gemini_engine import GeminiAnalysisEngine

def get_analyze_log_usecase() -> AnalyzeLogUseCase:
    # 1. Initialize Domain Services
    regex = RegexClassifier()
    
    # 2. Initialize Infrastructure
    vdb = FaissVectorStore()
    # Load index if it exists
    vdb.load("data/vector_index.bin", "data/metadata.pkl")
    
    job_manager_url = os.getenv("JOB_MANAGER_BASE_URL", "http://localhost:9000")
    job_manager_api_key = os.getenv("JOB_MANAGER_API_KEY")
    meta_repo = HttpJobMetadataGateway(base_url=job_manager_url, api_key=job_manager_api_key)
    engine = GeminiAnalysisEngine()
    
    # 3. Initialize Nodes
    nodes = AnalysisNodes(regex, meta_repo, vdb)
    
    # 4. Assemble UseCase
    return AnalyzeLogUseCase(nodes, engine)
