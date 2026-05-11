import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(websocket.router, tags=["Websocket"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to AegisHarness API",
        "docs_url": "/docs",
        "health_url": "/health"
    }

@app.get("/health")
async def health_check():
    print("[DEBUG] Health check requested")
    return {
        "status": "healthy", 
        "greptile_api_key_loaded": bool(os.getenv("GREPTILE_API_KEY")),
        "clod_api_key_loaded": bool(os.getenv("CLOD_API_KEY"))
    }

@app.post("/api/v1/system/restart")
async def restart_system():
    # 1. Total wipe: Delete the database file
    import os
    import pathlib
    import signal
    
    db_file = pathlib.Path("aegis.db")
    if db_file.exists():
        try:
            # We don't delete it here directly because it might be locked
            # Instead, we'll let the next startup handle the recreation
            # or just clear the tables. 
            # For a "hard" restart, we'll just kill the process.
            pass
        except:
            pass

    # 2. Hard exit: The watchdog or uvicorn --reload will pick it up
    print("[SYSTEM] HARD RESTART TRIGGERED - WIPING AND EXITING...")
    
    # Actually deleting the file is safer if we do it via a shell command right before exit
    os.system("rm -f aegis.db")
    
    # Send SIGTERM to self to trigger a clean-ish exit that uvicorn/watchdog can see
    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "resetting"}
