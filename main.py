from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib
import secrets
import shortuuid
from datetime import datetime, timedelta

from database import engine, SessionLocal, Base
from models import Room, Message

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Simple Encrypted Chat")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${pwd_hash}"


def cleanup_old_messages(db: Session):
    expire = datetime.utcnow() - timedelta(hours=24)
    db.query(Message).filter(Message.created_at < expire).delete()
    db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/create-room")
async def create_room_api(password: str = Form(...), db: Session = Depends(get_db)):
    if len(password) < 4:
        return JSONResponse({"error": "رمز باید حداقل ۴ کاراکتر باشد"}, status_code=400)

    room_code = shortuuid.ShortUUID().random(length=6).upper()
    new_room = Room(room_code=room_code, password_hash=hash_password(password))
    db.add(new_room)
    db.commit()

    return {
        "room_code": room_code,
        "password": password
    }


@app.get("/chat/{room_code}", response_class=HTMLResponse)
async def chat_page(request: Request, room_code: str):
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"room_code": room_code}
    )


class MessageIn(BaseModel):
    sender: str
    encrypted_content: str
    iv: str


@app.get("/api/messages/{room_code}")
def get_messages(room_code: str, db: Session = Depends(get_db)):
    cleanup_old_messages(db)
    messages = db.query(Message).filter(Message.room_code == room_code).order_by(Message.created_at).all()
    return {
        "messages": [
            {
                "sender": m.sender,
                "encrypted_content": m.encrypted_content,
                "iv": m.iv,
                "created_at": m.created_at.strftime("%H:%M")
            } for m in messages
        ]
    }


@app.post("/api/messages/{room_code}")
def send_message(room_code: str, data: MessageIn, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.room_code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="اتاق پیدا نشد")

    new_msg = Message(
        room_code=room_code,
        sender=data.sender,
        encrypted_content=data.encrypted_content,
        iv=data.iv
    )
    db.add(new_msg)
    db.commit()
    return {"status": "ok"}
