from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user_id, decode_token
from app.modules.chat.models import ChatRoom, ChatMessage
from app.websocket.manager import manager

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/rooms")
def get_my_rooms(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List chat rooms for the current user (donor or patient)."""
    rooms = db.query(ChatRoom).filter(
        (ChatRoom.donor_user_id == user_id) | (ChatRoom.patient_user_id == user_id)
    ).all()
    return [
        {
            "id": r.id,
            "request_id": r.request_id,
            "donor_user_id": r.donor_user_id,
            "patient_user_id": r.patient_user_id,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat(),
        }
        for r in rooms
    ]


@router.get("/rooms/{room_id}/messages")
def get_messages(
    room_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    """Get message history for a chat room."""
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(404, "Chat room not found")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.room_id == room_id)
        .order_by(ChatMessage.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": m.id,
            "room_id": m.room_id,
            "sender_id": m.sender_id,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/internal/create-room", status_code=201)
def create_room_internal(
    request_id: int,
    donor_user_id: int,
    patient_user_id: int,
    db: Session = Depends(get_db),
):
    """Internal endpoint to create a chat room. Called by consumer or core-service."""
    existing = db.query(ChatRoom).filter(ChatRoom.request_id == request_id).first()
    if existing:
        return {"id": existing.id, "status": "already_exists"}

    room = ChatRoom(
        request_id=request_id,
        donor_user_id=donor_user_id,
        patient_user_id=patient_user_id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return {"id": room.id, "status": "created"}


@router.websocket("/ws/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time chat.
    Connect: ws://host/api/v1/chat/ws/{room_id}?token=<jwt>
    """
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = int(payload["sub"])

    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        await websocket.close(code=4004)
        return

    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg = ChatMessage(room_id=room_id, sender_id=user_id, content=data)
            db.add(msg)
            db.commit()
            db.refresh(msg)
            await manager.broadcast(room_id, {
                "id": msg.id,
                "sender_id": user_id,
                "content": data,
                "created_at": msg.created_at.isoformat(),
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
