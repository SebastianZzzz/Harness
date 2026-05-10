import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from app.routers import tasks, websocket
from app.database import init_db

# Load environment variables from .env
load_dotenv()

app = FastAPI(
    title="AegisHarness API",
    description="Agentic Compiler & Guardrail Framework API",
    version="0.1.0",
    redirect_slashes=False,
)

TEST_UI_PATH = Path(__file__).with_name("test_ui.html")
DASHBOARD_PATH = Path(__file__).with_name("dashboard.html")
STATIC_DIR = Path(__file__).with_name("static")

@app.on_event("startup")
async def startup_event():
    await init_db()

# Allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(websocket.router, tags=["Websocket"])

@app.get("/")
async def dashboard_home():
    return FileResponse(DASHBOARD_PATH)

@app.get("/dashboard")
async def dashboard():
    return FileResponse(DASHBOARD_PATH)

@app.get("/test-ui")
async def test_ui():
    return FileResponse(TEST_UI_PATH)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "greptile_api_key_loaded": bool(os.getenv("GREPTILE_API_KEY")),
        "clod_api_key_loaded": bool(os.getenv("CLOD_API_KEY"))
    }
