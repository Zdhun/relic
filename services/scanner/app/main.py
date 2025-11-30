from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .ai.routes import router as ai_router

app = FastAPI(title="AuditAI Scanner")

# Allow CORS for dev (Next.js is on 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ai_router)

@app.get("/health")
def health():
    return {"status": "ok"}
