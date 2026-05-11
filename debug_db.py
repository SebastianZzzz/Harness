import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

async def test_init():
    print("Importing app.database...")
    from app.database import init_db, engine
    print("Calling init_db()...")
    try:
        await asyncio.wait_for(init_db(), timeout=10)
        print("init_db() success!")
    except asyncio.TimeoutError:
        print("init_db() TIMED OUT!")
    except Exception as e:
        print(f"init_db() FAILED: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_init())
