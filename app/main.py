from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.config import SECRET
from app.solver import solve_quiz_chain

app = FastAPI()

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.post("/solve")
async def solve_quiz(request: QuizRequest):
    if request.secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    try:
        result = await solve_quiz_chain(request.url, request.email, request.secret)
        return {"status": "completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
