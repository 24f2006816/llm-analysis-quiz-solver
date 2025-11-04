"""
FastAPI main application with /solve endpoint.
"""
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional
import asyncio

from app.config import SECRET, LOG_LEVEL, LOG_FORMAT
from app.solver import QuizSolver

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Analysis Quiz Solver",
    description="Backend API for solving LLM analysis quizzes",
    version="1.0.0"
)


class SolveRequest(BaseModel):
    """Request model for /solve endpoint."""
    email: str = Field(..., description="Email address")
    secret: str = Field(..., description="Secret key for authentication")
    url: str = Field(..., description="URL of the quiz to solve")
    
    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email address')
        return v
    
    @validator('url')
    def validate_url(cls, v):
        if not v or not v.startswith(('http://', 'https://')):
            raise ValueError('Invalid URL. Must start with http:// or https://')
        return v


class SolveResponse(BaseModel):
    """Response model for /solve endpoint."""
    success: bool
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LLM Analysis Quiz Solver API",
        "version": "1.0.0",
        "endpoints": {
            "/solve": "POST - Solve a quiz",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/solve", response_model=SolveResponse)
async def solve_quiz(request: SolveRequest):
    """
    Solve a quiz chain.
    
    Validates the secret, then:
    1. Scrapes the quiz URL using Playwright
    2. Extracts question, data files, and submission URL
    3. Computes the answer
    4. Submits the answer
    5. Automatically solves next quiz if available
    
    Returns:
        - 200: Success with results
        - 400: Invalid request (missing/invalid JSON or URL)
        - 403: Invalid secret
        - 500: Server error during solving
    """
    logger.info(f"Received solve request for URL: {request.url}")
    
    # Validate secret
    if request.secret != SECRET:
        logger.warning(f"Invalid secret provided for email: {request.email}")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: invalid secret"
        )
    
    # Validate URL
    if not request.url:
        logger.warning("Missing URL in request")
        raise HTTPException(
            status_code=400,
            detail="Missing or invalid URL"
        )
    
    try:
        # Create solver instance
        solver = QuizSolver(email=request.email, secret=request.secret)
        
        # Solve the quiz chain
        logger.info(f"Starting quiz solving for {request.url}")
        result = await solver.solve_quiz_chain(request.url)
        
        # Format response
        if result.get("success") or result.get("total_quizzes", 0) > 0:
            return SolveResponse(
                success=True,
                message=result.get("final_message", "Quiz solved successfully"),
                result=result
            )
        else:
            error_msg = result.get("errors", [{}])[0].get("error", "Unknown error") if result.get("errors") else "Failed to solve quiz"
            return SolveResponse(
                success=False,
                message="Failed to solve quiz",
                result=result,
                error=error_msg
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Error solving quiz: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT
    
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True
    )

