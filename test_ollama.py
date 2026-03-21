# test_simple.py
from langchain_ollama import ChatOllama

# 보유하신 모델 리스트 중 가장 작은 것
llm = ChatOllama(model="qwen3:1.7b", timeout=60) 

print("Sending request to Ollama...")
try:
    # 아주 짧은 질문 전달
    res = llm.invoke("Say 'Hello' in English")
    print("Response received:", res.content)
except Exception as e:
    print("Error:", e)