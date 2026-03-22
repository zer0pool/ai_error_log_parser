import json
import re
import bm25s
import chromadb
import logging
from typing import Annotated, Sequence, TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from Stemmer import Stemmer
from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection(name="airflow_errors")

# 전역 설정 (서버 시작 시 한 번만 로드)
bm25_retriever = bm25s.BM25.load("./bm25s_index", load_corpus=True)
with open("./bm25s_index/metadata.json", "r") as f:
    bm25_metadata = json.load(f)
stemmer = Stemmer("english")


# --- 1. Tools Definition ---
@tool
def search_error_guide(query: str):
    """
    30개 에러 클러스터 및 지식 베이스에서 관련 에러 가이드를 검색합니다.
    에러의 유형을 분류하거나 조치 방법을 찾을 때 사용하세요.
    """
    logger.info(f"🔍 search_error_guide called with query: {query}")
    result = hybrid_search(query)
    logger.info(f"✅ search_error_guide returned: {result[:100]}...")
    return result


def hybrid_search(query, top_k=2):
    """키워드(BM25S)와 의미(Vector) 검색 결과를 합칩니다."""
    logger.info(f"🔎 hybrid_search started with top_k={top_k}")
    
    # 1. BM25S 검색
    query_tokens = bm25s.tokenize([query], stemmer=stemmer)
    bm25_docs, _ = bm25_retriever.retrieve(query_tokens, k=top_k)
    logger.info(f"📄 BM25S retrieved {len(bm25_docs[0])} documents")
    
    # 2. Vector 검색 (collection 객체가 전역에 있다고 가정)
    vector_results = collection.query(query_texts=[query], n_results=top_k)
    logger.info(f"📊 Vector DB retrieved {len(vector_results['documents'][0])} documents")
    
    # 3. 중복 제거 및 컨텍스트 구성
    unique_contexts = set()
    
    # BM25S 결과 추가
    for doc in bm25_docs[0]:
        unique_contexts.add(f"[Keyword Match] {doc}")
        
    # Vector 결과 추가
    for doc in vector_results['documents'][0]:
        unique_contexts.add(f"[Semantic Match] {doc}")
    
    result = "\n\n".join(list(unique_contexts))
    logger.info(f"✨ hybrid_search combined {len(unique_contexts)} unique results")
    return result

@tool
def read_failed_source_code(file_path: str, line_number: int):
    """
    에러가 발생한 지점의 소스코드를 읽어옵니다.
    로그만으로 원인 파악이 어려울 때 로직상의 결함을 찾기 위해 사용하세요.
    """
    logger.info(f"📂 read_failed_source_code called - file: {file_path}, line: {line_number}")
    result = read_code_tool(file_path, line_number)
    logger.info(f"✅ read_failed_source_code returned code snippet")
    return result

def read_code_tool(file_path: str, line_number: int = None, window: int = 10):
    """실제 로컬 파일을 읽어 에러 발생 지점 주변 코드를 반환합니다."""
    try:
        logger.debug(f"📖 Reading file: {file_path}")
        # 보안을 위해 허용된 디렉토리 내 파일인지 체크하는 로직 권장
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if line_number:
            start = max(0, line_number - window)
            end = min(len(lines), line_number + window)
            code_snippet = "".join(lines[start:end])
            logger.info(f"📝 Extracted code snippet from line {start} to {end}")
            return f"--- Code Snippet ({file_path}) ---\n{code_snippet}"
        
        logger.info(f"📝 Returning first 100 lines of {file_path}")
        return "".join(lines[:100]) # 라인 번호 없으면 상단 일부 반환
    except Exception as e:
        error_msg = f"Error reading file: {str(e)}"
        logger.error(error_msg)
        return error_msg


tools = [search_error_guide, read_failed_source_code]
tool_node = ToolNode(tools)

# --- 2. State & Node Logic ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "Add messages to the list"]
    raw_log: str

model = ChatOllama(model="qwen2.5-coder:7b", temperature=0).bind_tools(tools)


def call_model(state: AgentState):
    messages = state['messages']
    
    # 시스템 프롬프트에서 '무조건 JSON'이라는 압박을 제거하고 단계를 나누어줍니다.
    system_prompt = """
    You are a Senior Airflow SRE Expert. 
    
    [PHASE 1: INVESTIGATION]
    - Your first priority is to gather evidence using tools.
    - To search for error guides, call 'search_error_guide'.
    - To read code, call 'read_failed_source_code'.
    - IMPORTANT: When using a tool, use the functional tool-calling feature. Do NOT just write a JSON string.

    [PHASE 2: FINAL REPORT]
    - ONLY after you have enough information from tool outputs, provide the final analysis.
    - The final analysis MUST be a JSON object with: error_id, category, technical_root_cause, evidence_line, resolution_step, confidence.
    - Return ONLY the JSON object as your final answer.
    """

    # 모델 호출 (ChatOllama의 bind_tools가 정상 작동하도록 유도)
    response = model.invoke([SystemMessage(content=system_prompt)] + list(messages))
    return {"messages": [response]}

def should_continue(state: AgentState):
    last_message = state['messages'][-1]
    
    # 1. 정상적인 도구 호출이 있는 경우
    if last_message.tool_calls:
        return "tools"
    
    # 2. 모델이 도구 호출을 텍스트(JSON)로 흉내 냈는지 체크 (나쁜 버릇 교정)
    if "search_error_guide" in last_message.content or "read_failed_source_code" in last_message.content:
        # 이 경우 다시 에이전트에게 "도구 호출 기능을 사용하라"고 피드백을 주며 되돌릴 수 있지만, 
        # 일단은 프롬프트 수정으로 해결하는 것이 가장 좋습니다.
        pass

    return END

# --- 3. Graph Construction ---
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "agent": "agent", END: END})
workflow.add_edge("tools", "agent")
app = workflow.compile()

# --- 4. Execution Logic ---
def run_analysis(error_log: str):
    logger.info("=" * 60)
    logger.info("🚀 Starting analysis")
    logger.info("=" * 60)
    
    # 초기 입력
    inputs = {
        "messages": [HumanMessage(content=f"Analyze this Airflow log and find the root cause. Please provide a detailed JSON report: {error_log}")],
        "raw_log": error_log
    }
    
    final_answer = ""
    iteration = 0
    # config에 recursion_limit을 줘서 무한 루프를 방지하되 충분히 생각할 시간을 줍니다.
    for output in app.stream(inputs, config={"recursion_limit": 15}):
        iteration += 1
        for node_name, state in output.items():
            print(f"\n[NODE: {node_name}]")
            last_msg = state["messages"][-1]

            # 1. AI가 도구를 호출하려고 할 때 (Action)
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                for tool_call in last_msg.tool_calls:
                    logger.info(f"[Iteration {iteration}] 🛠️  will call: {tool_call['name']}({tool_call['args']})")
                    print(f"🛠️  Action: {tool_call['name']}({tool_call['args']})")
            
            # 2. 도구가 실행된 결과가 나올 때 (Observation)
            elif node_name == "tools":
                logger.info(f"[Iteration {iteration}] 👁️  tool executed")
                print(f"👁️  Observation: {last_msg.content}")

            # 3. AI가 최종 답변을 텍스트로 내보낼 때 (Thought / Final Answer)
            elif last_msg.content:
                print(f"🧠  Thought/Answer: {last_msg.content}")
                logger.info(f"[Iteration {iteration}] 🧠  model response")
                final_answer = last_msg.content

    logger.info("=" * 60)
    logger.info("✅ Analysis completed")
    logger.info("=" * 60)
    return final_answer

if __name__ == "__main__":
        # Test Case: An error not in regex rules (Should trigger LLM)
    # sample_log = "pyarrow.lib.ArrowTypeError: Could not convert FLOAT64 to INT64 in destination table"
    # sample_log = "google.api_core.exceptions.Forbidden: 403 Access Denied: BigQuery BigQuery: Permission denied while getting Drive credentials."

    sample_log = """
    Caused by: com.google.cloud.spark.bigquery.repackaged.com.google.cloud.bigquery.BigQueryException: Error while reading data, error message: Schema mismatch: referenced variable 'df.list.element.PRODUCT_ID' has array levels of 1, while the corresponding field path to Parquet column has 0 repeated fields File: gs://my-recommendation/temp/.spark-bigquery-application_1683269466816_0014-881c60d3-da1a-44a3-92e3-a10de968b71c/part-00102-7f5d2b2b-22e2-4cf8-98fc-866eacc9c9db-c000.snappy.parquet
	at com.google.cloud.spark.bigquery.repackaged.com.google.cloud.bigquery.Job.reload(Job.java:419)
	at com.google.cloud.spark.bigquery.repackaged.com.google.cloud.bigquery.Job.waitFor(Job.java:252)
	at com.google.cloud.bigquery.connector.common.BigQueryClient.createAndWaitFor(BigQueryClient.java:333)
	at com.google.cloud.bigquery.connector.common.BigQueryClient.createAndWaitFor(BigQueryClient.java:323)
	at com.google.cloud.bigquery.connector.common.BigQueryClient.loadDataIntoTable(BigQueryClient.java:564)
	at com.google.cloud.spark.bigquery.write.BigQueryWriteHelper.loadDataToBigQuery(BigQueryWriteHelper.java:134)
	at com.google.cloud.spark.bigquery.write.BigQueryWriteHelper.writeDataFrameToBigQuery(BigQueryWriteHelper.java:107)
    """

    # sample_log = """
    # [2025-01-10 03:21:45,123] ERROR - Task failed with exception
    # Traceback (most recent call last):
    #   File "/usr/local/airflow/dags/etl_pipeline.py", line 42, in run_etl
    #     df = extract_from_db()
    #   File "/usr/local/airflow/dags/utils/db.py", line 88, in extract_from_db
    #     raise TimeoutError("Database connection timeout")
    # TimeoutError: Database connection timeout
    # """
    
    print("\n" + "="*60)
    print("🚀 STARTING AI AGENT MULTI-STEP ANALYSIS")
    print("="*60)
    
    result = run_analysis(sample_log)
    
    print("\n" + "="*60)
    print("🏁 FINAL ANALYSIS REPORT")
    print("="*60 + "\n")
    print(result)