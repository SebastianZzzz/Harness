from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # task_id -> list of active connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        # Send an initial connection success message
        await websocket.send_json({"type": "system", "message": "Connected to task logs"})

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast_state_change(self, task_id: str, new_phase: str, data: dict = None):
        """Broadcasts a phase change to all clients listening to a specific task."""
        if task_id in self.active_connections:
            payload = {
                "type": "state_change",
                "task_id": task_id,
                "phase": new_phase,
                "data": data or {}
            }
            # Create tasks to send concurrently
            send_tasks = []
            for connection in self.active_connections[task_id]:
                send_tasks.append(connection.send_json(payload))
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)
                
    async def broadcast_log(self, task_id: str, message: str):
        """Broadcasts an interim log message (Vibe Coding pulse)."""
        if task_id in self.active_connections:
            payload = {
                "type": "log",
                "task_id": task_id,
                "message": message
            }
            send_tasks = []
            for connection in self.active_connections[task_id]:
                send_tasks.append(connection.send_json(payload))
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)

manager = ConnectionManager()

@router.websocket("/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        while True:
            # We don't expect much from the client, just keep connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)
