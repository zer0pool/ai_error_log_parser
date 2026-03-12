from fastapi import APIRouter, Depends
from app.controller.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.controller.factory.analyze_log_factory import get_analyze_log_usecase
from app.application.usecase.analyze_log import AnalyzeLogUseCase

router = APIRouter(prefix="/api/v1")

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_log(
    req: AnalysisRequest,
    uc: AnalyzeLogUseCase = Depends(get_analyze_log_usecase)
):
    result = uc.execute(req.job_id, req.trace_log)
    analysis = result['analysis']
    
    return AnalysisResponse(
        job_id=req.job_id,
        category=analysis.category,
        cause=analysis.cause,
        guide=analysis.guide,
        confidence=analysis.confidence,
        logic=analysis.logic
    )
