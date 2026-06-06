from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.security import decode_token
from app.modules.chat.repository import ChatRepository
from app.modules.chat.schemas import ChatRoomOut, MessageOut, SendMessage
from app.websocket.manager import manager

router = APIRouter(prefix="/chat", tags=["Chat"])


def _repo(db: Session = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)


@router.get("/rooms", response_model=list[ChatRoomOut])
def get_my_rooms(
    repo: ChatRepository = Depends(_repo),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.modules.donors.repository import DonorRepository
    from app.modules.patients.repository import PatientRepository
    donor = DonorRepository(db).get_by_user_id(current_user.id)
    patient = PatientRepository(db).get_by_user_id(current_user.id)
    return repo.get_rooms_for_user(
        donor_id=donor.id if donor else None,
        patient_id=patient.id if patient else None,
    )


@router.get("/rooms/{room_id}/messages", response_model=list[MessageOut])
def get_messages(
    room_id: int,
    skip: int = 0,
    limit: int = 50,
    repo: ChatRepository = Depends(_repo),
    _=Depends(get_current_user),
):
    room = repo.get_room(room_id)
    if not room:
        raise HTTPException(404, "Chat room not found")
    return repo.get_messages(room_id, skip, limit)


@router.websocket("/ws/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Connect via: ws://localhost:8000/api/v1/chat/ws/{room_id}?token=<access_token>
    """
    # Authenticate via query param token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = int(payload["sub"])
    repo = ChatRepository(db)

    room = repo.get_room(room_id)
    if not room:
        await websocket.close(code=4004)
        return

    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg = repo.save_message(room_id=room_id, sender_id=user_id, content=data)
            await manager.broadcast(room_id, {
                "id": msg.id,
                "sender_id": user_id,
                "content": data,
                "created_at": msg.created_at.isoformat(),
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
