from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.application.usecase.analyze_log_state import AnalyzeLogState
from app.application.nodes.analysis_nodes import AnalysisNodes
from app.domain.repository.analysis_engine import AnalysisEngine

class AnalyzeLogUseCase:
    def __init__(self, nodes: AnalysisNodes, engine: AnalysisEngine):
        self.nodes = nodes
        self.engine = engine
        self.graph = self._build_graph()

    def _verify_llm(self, state: AnalyzeLogState) -> Dict[str, Any]:
        """
        The bridge node between LangGraph and the Domain AnalysisEngine.
        """
        result = self.engine.analyze(
            trace_log=state['trace_log'],
            regex_category=state.get('regex_category', 'Unknown'),
            job_metadata=state['job_metadata'],
            context_docs=state['retrieved_docs']
        )
        return {"analysis": result}

    def _build_graph(self):
        workflow = StateGraph(AnalyzeLogState)
        
        workflow.add_node("classify", self.nodes.classify_regex)
        workflow.add_node("metadata", self.nodes.fetch_job_metadata)
        workflow.add_node("retrieve", self.nodes.retrieve_docs)
        workflow.add_node("verify", self._verify_llm)
        
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "metadata")
        workflow.add_edge("metadata", "retrieve")
        workflow.add_edge("retrieve", "verify")
        workflow.add_edge("verify", END)
        
        return workflow.compile()

    def execute(self, job_id: str, trace_log: str) -> Dict[str, Any]:
        initial_state = {
            "job_id": job_id,
            "trace_log": trace_log,
            "retrieved_docs": [],
            "errors": []
        }
        return self.graph.invoke(initial_state)
