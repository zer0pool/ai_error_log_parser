import os
import json
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from app.domain.entity.analysis import AnalysisResult, JobMetadata
from app.domain.repository.analysis_engine import AnalysisEngine

class GeminiAnalysisEngine(AnalysisEngine):
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.llm = ChatGoogleGenerativeAI(model=model_name)

    def analyze(
        self, 
        trace_log: str, 
        regex_category: str, 
        job_metadata: JobMetadata, 
        context_docs: List[str]
    ) -> AnalysisResult:
        context_str = "\n".join(context_docs)

        # Use the tail of the log - the most recent lines contain the actual error
        log_tail = trace_log[-3000:]

        prompt = f"""
        You are an Airflow and Data Platform expert. Your task is to analyze an execution failure and provide a structured JSON report.

        ### Input Data:
        1. **Trace Log (Tail - Most Recent Lines)**: {log_tail}
        2. **Initial Regex Category**: {regex_category}
        3. **Job Metadata**: {job_metadata.model_dump_json()}
        4. **Domain Knowledge & Similar Past Cases**: 
        {context_str}

        ### Instructions:
        - **IMPORTANT**: The trace log shown is the TAIL (most recent portion) of the full log. Prioritize errors and exceptions found here.
        - **Filename Analysis**: Carefully identify any file path or script names mentioned in the log (e.g., `.py`, `.sql`, `.ipynb`, `.sh` files). 
          These filenames are strong hints about the type of operation being performed (e.g., a `.sql` file suggests a SQL transformation, a `.py` script suggests a Python notebook or custom operator).
          Incorporate this insight into your root cause analysis.
        - Analyze the **Trace Log** and **Job Metadata** in conjunction with the provided **Domain Knowledge**.
        - If the **Initial Regex Category** is "Unknown" or seems incorrect based on the log, propose a more accurate category.
        - Provide a technical **Root Cause Analysis**.
        - Provide an actionable, step-by-step **Resolution Guide**.
        - Assign a **Confidence Score** (0.0 to 1.0) based on the following criteria:
            - **0.9 - 1.0**: Exact pattern match found in domain knowledge or historical logs. No ambiguity.
            - **0.7 - 0.9**: Strong logical inference based on job type (SQL/Notebook) and common platform failures.
            - **0.5 - 0.7**: Plausible root cause identified, but the log is partially ambiguous or information is missing.
            - **Below 0.5**: Low certainty. High ambiguity or conflicting evidence.
        - Use the **logic** field to explain your reasoning process and why you chose that confidence score.

        ### Output Format (Strict JSON):
        {{
            "category": "String (e.g., BQ_SCHEMA_MISMATCH, GKE_OOM)",
            "cause": "String (Detailed technical explanation, mentioning identified filenames if relevant)",
            "guide": "String (Actionable steps)",
            "confidence": 0.0,
            "logic": "String (Description of the reasoning process, including filename analysis)"
        }}
        """

        # In a real scenario, use structured output or a parser
        response = self.llm.invoke(prompt)
        content = response.content

        # Basic JSON extraction logic (could be improved with PydanticOutputParser)
        try:
            data = json.loads(content[content.find('{'):content.rfind('}')+1])
            return AnalysisResult(**data)
        except Exception:
            # Fallback if LLM output is malformed
            return AnalysisResult(
                category=regex_category,
                cause="Automatic analysis failed to parse LLM response.",
                guide="Please refer to the trace log and manual investigation.",
                confidence=0.5
            )
