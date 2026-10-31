import asyncio
import json
import re
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.session_store import session_store
from app.models.messages import AgentMessage

sse_router = APIRouter()

SAFE_SESSION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


async def message_streamer(session_id: str) -> AsyncGenerator[str, None]:
    """Stream agent protocol messages live as Server-Sent Events (SSE)."""
    rec = session_store.get_by_session_id(session_id)
    if not rec:
        yield f"data: {json.dumps({'error': True, 'message': 'Session not found'})}\n\n"
        return

    # Yield all historical messages first
    for msg in rec.messages:
        yield f"data: {json.dumps(msg)}\n\n"
        await asyncio.sleep(0.05)

    # Send completion indicator
    yield f"data: {json.dumps({'event': 'stream_complete', 'session_id': session_id})}\n\n"


@sse_router.get("/api/diagnosis/{session_id}/stream")
async def stream_agent_messages(session_id: str):
    if not session_id or len(session_id) > 64 or not SAFE_SESSION_ID_REGEX.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    return StreamingResponse(
        message_streamer(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
