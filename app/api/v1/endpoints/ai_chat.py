from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_service import F1StrategistEngine

router = APIRouter()

try:
    ai_engine = F1StrategistEngine()
except Exception as e:
    print(f"❌ Error initializing F1StrategistEngine: {e}")
    ai_engine = None

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

@router.post("/query-insights", response_model=QueryResponse)
async def get_f1_insights(payload: QueryRequest):
    if ai_engine is None:
        raise HTTPException(status_code=503, detail="AI Engine offline.")
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    try:
        ai_response = ai_engine.query_assistant(payload.question)
        return QueryResponse(answer=ai_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))