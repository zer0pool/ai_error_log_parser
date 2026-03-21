import re
import json
from typing import TypedDict, Optional, List
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import json
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
import bm25s
from Stemmer import Stemmer


# DB 및 모델 미리 로드 (전역 혹은 싱글톤 추천)
embed_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection(name="airflow_errors")

# 전역 설정 (서버 시작 시 한 번만 로드)
bm25_retriever = bm25s.BM25.load("./bm25s_index", load_corpus=True)
with open("./bm25s_index/metadata.json", "r") as f:
    bm25_metadata = json.load(f)
stemmer = Stemmer("english")

 
 
 

def load_rules(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 이미지의 JSON 구조에 맞춰서 Regex 패턴 리스트 생성
        rules = []
        for item in data:
            rules.append({
                "pattern": item.get("pattern"),
                "id": item.get("error_id"),
                "category": item.get("category")
            })
        return rules

# --- 1. State & Model Definition ---
class AgentState(TypedDict):
    raw_log: str
    is_identified: bool
    final_report: Optional[dict]

# 1. 파일에서 규칙을 로드하는 함수
def load_error_definitions(file_path: str = "data/error_definitions.json"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Using empty rules.")
        return []

# [개념적 흐름]
def rerank_node(state: AgentState):
    query = state["raw_log"]
    candidates = state["retrieved_docs"] # Vector DB에서 찾은 5개
    
    # 리랭커 모델이 query와 candidates를 1:1로 비교해서 점수 부여
    ranked_docs = reranker.compute_score(query, candidates)
    
    # 가장 점수가 높은 상위 2개만 LLM에게 전달
    return {"final_context": ranked_docs[:2]}


# 2. 수정된 노드 함수
def regex_branch_node(state: AgentState):
    """Phase 1: Fast Regex Matching using external JSON"""
    log = state["raw_log"]
    
    # 매번 파일을 읽기 부담스럽다면 전역 변수로 빼거나 캐싱할 수 있습니다.
    error_definitions = load_error_definitions()
        
    for item in error_definitions:
            # 1. [VAR]를 어떤 문자든 올 수 있는 .* 로 치환
            # 2. pattern에 특수문자가 섞여 있을 수 있으므로 주의해서 구성
            pattern = item["pattern"].replace("[VAR]", r".*")
            
            # re.search는 문장 중간에 패턴이 있어도 찾아냅니다.
            match = re.search(pattern, log, re.IGNORECASE)
            
            if match:
                return {
                    "is_identified": True,
                    "final_report": {
                        "error_id": item["error_id"],
                        "category": item.get("category", "PERMISSION"),
                        "analysis_method": "Deterministic_Regex",
                        "technical_root_cause": item.get("description"),
                        "resolution_step": item.get("resolution_step"),
                        "evidence_line": match.group(0), # 매칭된 부분 추출
                        "confidence": 1.0
                    }
                }
            
    # 매칭되는 것이 없으면 2차 분석(LLM)으로 넘김
    return {"is_identified": False}

def hybrid_search(query, top_k=2):
    """키워드(BM25S)와 의미(Vector) 검색 결과를 합칩니다."""
    # 1. BM25S 검색
    query_tokens = bm25s.tokenize([query], stemmer=stemmer)
    bm25_docs, _ = bm25_retriever.retrieve(query_tokens, k=top_k)
    
    # 2. Vector 검색 (collection 객체가 전역에 있다고 가정)
    vector_results = collection.query(query_texts=[query], n_results=top_k)
    
    # 3. 중복 제거 및 컨텍스트 구성
    unique_contexts = set()
    
    # BM25S 결과 추가
    for doc in bm25_docs[0]:
        unique_contexts.add(f"[Keyword Match] {doc}")
        
    # Vector 결과 추가
    for doc in vector_results['documents'][0]:
        unique_contexts.add(f"[Semantic Match] {doc}")
        
    return "\n\n".join(list(unique_contexts))

def llm_analysis_node(state: AgentState):
    """
    Phase 2: Deep AI Analysis with Hybrid Retrieval and Confidence Filtering
    """
    log = state["raw_log"]
    operator_name = state.get("operator_name", "UnknownOperator")
    operator_hint = state.get("operator_hint", "")

    # 1. 하이브리드 검색을 통해 관련 가이드 추출
    combined_context = hybrid_search(log)

    # 2. Ollama 모델 설정 (Qwen 2.5 또는 Llama 3.1)
    llm = ChatOllama(
        model="qwen2.5-coder:7b", 
        temperature=0, 
        format="json",
        timeout=120  # CPU 실행 시 넉넉하게 설정
    )

    # 3. 프롬프트 구성 (신뢰도 강제 및 UNKNOWN 가이드 포함)
    prompt = ChatPromptTemplate.from_template("""
    You are a Senior Airflow Site Reliability Engineer. 
    Analyze the following error log from a '{operator_name}'.
    {operator_hint}

    [Reference Guides]:
    {context}
    - ID: UNKNOWN | Desc: Any other errors not matching the guides above.

    [Error Log]:
    {log}

    [Strict Instructions]:
    1. Analyze the log based ONLY on the provided Reference Guides.
    2. If the log matches a guide, provide its 'error_id'.
    3. If NO guide matches strictly (confidence < 0.7), you MUST:
       - Set 'error_id' to "UNKNOWN"
       - Set 'confidence' to a value below 0.5
       - Set 'resolution_step' to "New unknown error. Developer check required."
    4. Provide the 'confidence' as a FLOAT between 0.0 and 1.0.

    Return ONLY a JSON object with: 
    error_id, category, technical_root_cause, evidence_line, resolution_step, confidence.
    """)

    # 4. LLM 실행
    chain = prompt | llm
    try:
        response = chain.invoke({
            "operator_name": operator_name,
            "operator_hint": operator_hint,
            "context": combined_context,
            "log": log
        })
        
        report = json.loads(response.content)
        
        # 5. 신뢰도(Confidence) 숫자형 변환 및 안전 필터링
        try:
            conf_score = float(report.get("confidence", 0))
            if conf_score > 1: conf_score /= 100.0  # 95 -> 0.95 변환
        except (ValueError, TypeError):
            conf_score = 0.0

        # 신뢰도 임계치(0.7) 미달 시 UNKNOWN 리포트로 강제 전환
        if conf_score < 0.7 or report.get("error_id") == "UNKNOWN":
            return {
                "is_identified": True,
                "final_report": {
                    "error_id": "UNKNOWN",
                    "category": "Unclassified",
                    "technical_root_cause": "Low confidence match or entirely new error pattern.",
                    "evidence_line": report.get("evidence_line", "N/A"),
                    "resolution_step": "Manual investigation required. Please update the error guide if solved.",
                    "confidence": conf_score,
                    "analysis_method": "AI_Hybrid_Low_Confidence"
                }
            }

        # 최종 리포트 확정
        report["confidence"] = conf_score
        report["analysis_method"] = "AI_Hybrid_Search_Analysis"
        return {"is_identified": True, "final_report": report}

    except Exception as e:
        print(f"Error in LLM node execution: {e}")
        return {"is_identified": False}

def preprocess_log_node(state: AgentState):
    raw_log = state["raw_log"]
    
    # 1. Traceback 이후만 남기기 (가장 흔한 에러 시작점)
    if "Traceback (most recent call last):" in raw_log:
        distilled_log = raw_log.split("Traceback (most recent call last):")[-1]
    else:
        # Traceback이 없으면 마지막 2000자만 추출 (약 50~100줄)
        distilled_log = raw_log[-2000:]

    # 2. Jupyter 특유의 긴 코드 블록이나 불필요한 메타데이터 제거 (정규식)
    # 예: "Input In [1], in <cell line: 5>..." 같은 노이즈 정제
    distilled_log = re.sub(r'Input In \[\d+\].+', '', distilled_log)
    
    # 3. 빈 줄 제거 및 가독성 확보
    lines = [line.strip() for line in distilled_log.split('\n') if line.strip()]
    
    # 너무 길면 LLM이 헷갈리므로 최종 50줄로 제한
    final_log = "\n".join(lines[-50:])
    
    print(f"[*] Log distilled from {len(raw_log)} to {len(final_log)} characters.")
    
    return {"raw_log": final_log} # 이후 노드들은 이 정제된 로그를 사용

def draw_mermaid_graph(app):
    """
    LangGraph 객체의 구조를 Mermaid 텍스트 형식으로 출력합니다.
    복사하여 https://mermaid.live/ 에서 시각화할 수 있습니다.
    """
    try:
        # Mermaid 형식의 텍스트 추출
        mermaid_code = app.get_graph().draw_mermaid()
        
        print("\n" + "="*50)
        print(" [LangGraph Structure - Mermaid Text] ")
        print(" Copy the text below and paste it into https://mermaid.live/")
        print("="*50 + "\n")
        
        print(mermaid_code)
        
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"Error generating Mermaid text: {e}")
 
        
# --- 3. Graph Construction (Updated) ---

workflow = StateGraph(AgentState)

# 노드 등록
workflow.add_node("check_regex", regex_branch_node)
workflow.add_node("preprocess_log", preprocess_log_node) 
workflow.add_node("analyze_llm", llm_analysis_node)

# 시작점 설정
workflow.set_entry_point("check_regex")

# 조건부 로직: 정규식 실패 시 '전처리' 단계로 이동
def should_continue(state: AgentState):
    if state["is_identified"]:
        return "end"
    return "preprocess"

workflow.add_conditional_edges(
    "check_regex",
    should_continue,
    {
        "end": END, 
        "preprocess": "preprocess_log" # 정규식 실패 시 전처리 노드로!
    }
)

# 전처리가 끝나면 LLM 분석으로 연결
workflow.add_edge("preprocess_log", "analyze_llm")
workflow.add_edge("analyze_llm", END)

app = workflow.compile()


# 함수 호출 (app 객체를 전달)
# draw_mermaid_graph(app)


# --- 4. Execution ---
if __name__ == "__main__":
    # Test Case: An error not in regex rules (Should trigger LLM)
    # sample_log = "pyarrow.lib.ArrowTypeError: Could not convert FLOAT64 to INT64 in destination table"
    # sample_log = "google.api_core.exceptions.Forbidden: 403 Access Denied: BigQuery BigQuery: Permission denied while getting Drive credentials."

    # sample_log = """
    # Caused by: com.google.cloud.spark.bigquery.repackaged.com.google.cloud.bigquery.BigQueryException: Error while reading data, error message: Schema mismatch: referenced variable 'df.list.element.PRODUCT_ID' has array levels of 1, while the corresponding field path to Parquet column has 0 repeated fields File: gs://my-recommendation/temp/.spark-bigquery-application_1683269466816_0014-881c60d3-da1a-44a3-92e3-a10de968b71c/part-00102-7f5d2b2b-22e2-4cf8-98fc-866eacc9c9db-c000.snappy.parquet
	# at com.google.cloud.spark.bigquery.repackaged.com.google.cloud.bigquery.Job.reload(Job.java:419)
	# at com.google.cloud.spark.bigquery.repackaged.com.google.cloud.bigquery.Job.waitFor(Job.java:252)
	# at com.google.cloud.bigquery.connector.common.BigQueryClient.createAndWaitFor(BigQueryClient.java:333)
	# at com.google.cloud.bigquery.connector.common.BigQueryClient.createAndWaitFor(BigQueryClient.java:323)
	# at com.google.cloud.bigquery.connector.common.BigQueryClient.loadDataIntoTable(BigQueryClient.java:564)
	# at com.google.cloud.spark.bigquery.write.BigQueryWriteHelper.loadDataToBigQuery(BigQueryWriteHelper.java:134)
	# at com.google.cloud.spark.bigquery.write.BigQueryWriteHelper.writeDataFrameToBigQuery(BigQueryWriteHelper.java:107)
    # """

    sample_log = """
    [2025-01-10 03:21:45,123] {taskinstance.py:1770} ERROR - Task failed with exception
    Traceback (most recent call last):
    File "/usr/local/airflow/dags/etl_pipeline.py", line 42, in run_etl
        df = extract_from_db()
    File "/usr/local/airflow/dags/utils/db.py", line 88, in extract_from_db
        raise TimeoutError("Database connection timeout")
    TimeoutError: Database connection timeout
    """

    print("--- Running Analysis ---")
    result = app.invoke({"raw_log": sample_log})
    
    if result["is_identified"]:
        print(json.dumps(result["final_report"], indent=2))
    else:
        print("Analysis failed to identify the error.")