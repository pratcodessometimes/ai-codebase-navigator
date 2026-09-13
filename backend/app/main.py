from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.repository import router as repository_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    repository_router,
    prefix="/api/repository"
)


@app.get("/")
def root():
    return {"message": "AI Codebase Navigator API is running"}