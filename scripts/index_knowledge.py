import os
import sys
import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.infrastructure.vector_db.faiss_store import FaissVectorStore

def index_domain_knowledge(vdb: FaissVectorStore, doc_path: str):
    if not os.path.exists(doc_path):
        print(f"Warning: Domain knowledge file {doc_path} not found.")
        return

    print(f"Indexing domain knowledge from {doc_path}...")
    with open(doc_path, 'r') as f:
        content = f.read()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)
    
    metadatas = [{"source": "domain_knowledge", "content": chunk} for chunk in chunks]
    vdb.add_texts(chunks, metadatas)

def index_processed_logs(vdb: FaissVectorStore, csv_path: str):
    if not os.path.exists(csv_path):
        print(f"Warning: Processed logs CSV {csv_path} not found. Skipping log indexing.")
        return

    print(f"Indexing processed logs from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Use the representative original log for semantic search
    texts = df['representative_log'].tolist()
    metadatas = [
        {
            "source": "historical_log", 
            "pattern": row['cleaned_pattern'], 
            "count": row['occurrence_count'],
            "content": row['representative_log']
        } 
        for _, row in df.iterrows()
    ]
    
    vdb.add_texts(texts, metadatas)

if __name__ == "__main__":
    INDEX_PATH = "data/vector_index.bin"
    METADATA_PATH = "data/metadata.pkl"
    DOMAIN_DOC = "docs/domain_knowledge.md"
    PROCESSED_LOGS = "data/processed_patterns.csv"

    vdb = FaissVectorStore()
    
    # 1. Index domain documents
    index_domain_knowledge(vdb, DOMAIN_DOC)
    
    # 2. Index historical patterns (if available)
    index_processed_logs(vdb, PROCESSED_LOGS)
    
    # 3. Save
    os.makedirs("data", exist_ok=True)
    vdb.save(INDEX_PATH, METADATA_PATH)
    print("Vector DB initialization complete.")
