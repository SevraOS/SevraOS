"""
HELIOS OS + SEVRA AI
Dashboard WebSocket Endpoints (Section 10)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from dashboard.websocket.manager import ws_manager
from dashboard.api.dependencies import get_current_user

router = APIRouter()

@router.websocket("/stream")
async def websocket_stream(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    Main Multiplexed WebSocket Endpoint.
    Client provides JWT in query params.
    """
    # 1. Authenticate via token
    # Using a sync wrapper around get_current_user logic for WS
    from fastapi.security import HTTPAuthorizationCredentials
    from fastapi import HTTPException
    from dashboard.api.dependencies import get_current_user
    
    try:
        user = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
        user_id = user.get("sub", "anonymous")
    except HTTPException:
        await websocket.close(code=1008) # Policy Violation
        return

    # 2. Connect
    await ws_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive commands from client (e.g., {"action": "subscribe", "channel": "patient:123:vitals"})
            data = await websocket.receive_json()
            action = data.get("action")
            channel = data.get("channel")
            
            if action == "subscribe" and channel:
                # Basic RBAC could be applied here: Can user see this patient?
                await ws_manager.subscribe_user(user_id, channel)
                await websocket.send_json({"status": "subscribed", "channel": channel})
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
