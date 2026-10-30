
from datetime import datetime, timedelta
from typing import Optional

from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    Header,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import shortuuid
import json

from app.database import engine, get_db, Base, SessionLocal
from app.models import Room, Message
from app.security import hash_password, verify_password, create_access_token, decode_access_token
from app.redis_manager import manager

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Encrypted Chatroom")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup():
    await manager.init_redis()


@app.on_event("shutdown")
async def shutdown():
    await manager.close()


def cleanup_old_messages(db: Session):
    expire = datetime.utcnow() - timedelta(hours=24)
    db.query(Message).filter(Message.created_at < expire).delete()
    db.commit()


def require_room_token(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="توکن لازم است")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    return payload


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/create-room")
async def create_room(password: str = Form(...), db: Session = Depends(get_db)):
    if len(password) < 8:
        return JSONResponse(
            {"error": "رمز باید حداقل ۸ کاراکتر باشد"},
            status_code=400,
        )
    room_code = shortuuid.ShortUUID().random(length=6).upper()
    room = Room(room_code=room_code, password_hash=hash_password(password))
    db.add(room)
    db.commit()
    return {"room_code": room_code}


@app.post("/api/join-room")
async def join_room(
    room_code: str = Form(...),
    password: str = Form(...),
    sender: str = Form(...),
    db: Session = Depends(get_db),
):
    room_code = room_code.strip().upper()
    sender = sender.strip()[:64] or "ناشناس"
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room or not verify_password(password, room.password_hash):
        raise HTTPException(status_code=403, detail="کد اتاق یا رمز اشتباه است")
    token = create_access_token(room_code, sender)
    return {"access_token": token, "room_code": room_code, "sender": sender}


@app.get("/chat/{room_code}", response_class=HTMLResponse)
async def chat_page(request: Request, room_code: str):
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"room_code": room_code.upper()},
    )


class MessageOut(BaseModel):
    sender: str
    encrypted_content: str
    iv: str
    created_at: str


@app.get("/api/messages/{room_code}")
def get_messages(
    room_code: str,
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_room_token),
):
    room_code = room_code.upper()
    if token_data.get("sub") != room_code:
        raise HTTPException(status_code=403, detail="دسترسی به این اتاق ندارید")
    cleanup_old_messages(db)
    rows = (
        db.query(Message)
        .filter(Message.room_code == room_code)
        .order_by(Message.created_at)
        .all()
    )
    return {
        "messages": [
            {
                "sender": m.sender,
                "encrypted_content": m.encrypted_content,
                "iv": m.iv,
                "created_at": m.created_at.strftime("%H:%M"),
            }
            for m in rows
        ]
    }


class MessageIn(BaseModel):
    encrypted_content: str = Field(..., min_length=1)
    iv: str = Field(..., min_length=1)


@app.post("/api/messages/{room_code}")
async def send_message_http(
    room_code: str,
    data: MessageIn,
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_room_token),
):
    room_code = room_code.upper()
    if token_data.get("sub") != room_code:
        raise HTTPException(status_code=403, detail="دسترسی ندارید")
    sender = token_data.get("sender", "ناشناس")
    msg = Message(
        room_code=room_code,
        sender=sender,
        encrypted_content=data.encrypted_content,
        iv=data.iv,
    )
    db.add(msg)
    db.commit()
    payload = {
        "type": "chat",
        "sender": sender,
        "encrypted_content": data.encrypted_content,
        "iv": data.iv,
        "time": datetime.utcnow().strftime("%H:%M"),
    }
    await manager.publish(room_code, payload)
    return {"status": "ok"}


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    room_code = room_code.upper()
    token = websocket.query_params.get("token")
    payload = decode_access_token(token) if token else None
    if not payload or payload.get("sub") != room_code:
        await websocket.close(code=4401)
        return

    await manager.connect(websocket, room_code)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type", "chat")
            if msg_type == "chat":
                enc = message.get("encrypted_content") or message.get("content")
                iv = message.get("iv", "")
                if not enc or not iv:
                    continue
                sender = payload.get("sender", "ناشناس")
                db = SessionLocal()
                try:
                    db.add(
                        Message(
                            room_code=room_code,
                            sender=sender,
                            encrypted_content=enc,
                            iv=iv,
                        )
                    )
                    db.commit()
                finally:
                    db.close()

                await manager.publish(
                    room_code,
                    {
                        "type": "chat",
                        "sender": sender,
                        "encrypted_content": enc,
                        "iv": iv,
                        "time": datetime.utcnow().strftime("%H:%M"),
                    },
                )
            elif msg_type in ("file_start", "file_chunk", "file_request_chunks", "file_end"):
                await manager.publish(room_code, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)