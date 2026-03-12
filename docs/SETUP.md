# Getting Started: New Environment Setup Guide

This guide covers every step required to set up the AI Log Analysis Service on a new machine, from scratch.

---

## Prerequisites
- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)**: Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **API Keys** (see Step 2)

---

## Step 1: Clone the Repository
```bash
git clone <repo-url>
cd ai_log
```

---

## Step 2: Configure Environment Variables
Copy the example and fill in your actual keys:
```bash
cp .env.example .env   # or edit .env directly
```

Edit `.env`:
```ini
GOOGLE_API_KEY="AIza..."                    # Required: Gemini API key (aistudio.google.com/app/apikey)
LANGCHAIN_TRACING_V2=false                  # Set to true if you have a LangSmith account
LANGCHAIN_API_KEY="..."                     # Only needed if tracing is enabled

JOB_MANAGER_BASE_URL="http://your-server"  # Internal job-manager service URL
JOB_MANAGER_API_KEY="..."                  # Job-manager API key (if required)
```

---

## Step 3: Install Dependencies
```bash
make install
```
This runs `uv sync` and installs everything from `uv.lock`.

---

## Step 4: Prepare Raw Log Files
Place your raw Airflow error log CSV files in **`data/raw/`**.

### CSV Format (required columns):
| Column | Description |
|--------|-------------|
| `id` | Unique row ID (integer) |
| `trace_log` | Full Airflow traceback text |

Example:
```
id,trace_log
1,"ERROR fin_history_sensor_order_table failed. Timeout after 72 hours."
2,"google.cloud.bigquery.dbapi.OperationalError: 400 Provided Schema does not match..."
```

> 더미 데이터가 필요하다면 `data/raw/` 에 이미 10개의 샘플 파일(총 1,000건)이 포함되어 있습니다.

---

## Step 5: Build the Vector Database
```bash
make setup-data
```

이 명령은 두 단계를 순서대로 실행합니다:

### 5-1. 로그 전처리 (`scripts/batch_process.py`)
- `data/raw/*.csv` 파일을 모두 읽고 합칩니다
- 동적 요소(타임스탬프, ID, UUID)를 제거하여 패턴을 추출합니다
- 중복 제거 후 빈도순으로 정렬합니다
- 결과: `data/processed_patterns.csv`

### 5-2. Vector DB 인덱싱 (`scripts/index_knowledge.py`)
아래 두 가지 소스를 FAISS에 임베딩합니다:

| 소스 | 경로 | 역할 |
|------|------|------|
| 도메인 지식 | `docs/domain_knowledge.md` | Airflow 아키텍처, 제약 조건 설명 |
| 정제된 로그 패턴 | `data/processed_patterns.csv` | 과거 에러 사례 |

- 결과: `data/vector_index.bin`, `data/metadata.pkl`

> ⚠️ `docs/domain_knowledge.md`에 서비스 특화 정보(테이블명, SA 계정, 제약 조건 등)를 추가할수록 분석 품질이 높아집니다.

---

## Step 6: Start the Service

### API Server
```bash
make run-api
# → http://localhost:8000/docs (Swagger UI)
```

### Admin Dashboard (Optional)
```bash
make run-admin
# → http://localhost:8501
```

---

## Troubleshooting

| 증상 | 해결 방법 |
|------|----------|
| `ModuleNotFoundError: No module named 'app'` | `make run-api` 사용 (직접 `python app/main.py` 실행 금지) |
| `API key not valid` | `.env`의 `GOOGLE_API_KEY` 확인 |
| `model not found` | `gemini_engine.py`의 모델명을 `gemini-2.0-flash`로 확인 |
| Vector DB가 없다는 에러 | `make setup-data` 재실행 |
| Job metadata API 연결 실패 | `.env`의 `JOB_MANAGER_BASE_URL` 확인. 실패 시 기본값(`Unknown`)으로 fallback됨 |

---

## Quick Reference
```bash
make install       # 의존성 설치
make setup-data    # 로그 전처리 + VDB 인덱싱 (데이터 변경 시 재실행)
make run-api       # API 서버 시작
make run-admin     # 관리자 대시보드 시작
make add pkg=...   # 새 패키지 추가
make clean         # 가상환경 삭제
```
