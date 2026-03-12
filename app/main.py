from fastapi import FastAPI
from app.controller.router.analysis import router as analysis_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Airflow AI Log Analyzer")

app.include_router(analysis_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
