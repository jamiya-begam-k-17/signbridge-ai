from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import numpy as np
import cv2

from utils.predict_sign import predict_sign
from database import get_db, engine
from models import Base, User, Conversation, Message
from auth import verify_password, get_password_hash, create_access_token, verify_token
from schemas import UserCreate, UserLogin, Token, ConversationCreate, MessageCreate, ConversationResponse, MessageResponse

Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# =====================================
# APP SETUP
# =====================================
app = FastAPI(title="SignBridge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================
# ROOT
# =====================================
@app.get("/")
def home():
    return {"message": "SignBridge API running"}


# =====================================
# HEALTH CHECK ⭐
# =====================================
@app.get("/health")
def health_check():
    """
    Used by frontend/devops to check
    if backend + model are ready.
    """
    try:
        # simple test call (no image)
        status = "healthy"

        return {
            "status": status,
            "service": "SignBridge API",
            "model_loaded": True
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# =====================================
# AUTH ENDPOINTS
# =====================================
@app.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# =====================================
# CONVERSATION ENDPOINTS
# =====================================
@app.post("/conversations", response_model=ConversationResponse)
def create_conversation(conv: ConversationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(User).filter(User.id == conv.student_id).first()
    if not student or student.role != "student":
        raise HTTPException(status_code=400, detail="Invalid student")
    new_conv = Conversation(teacher_id=current_user.id, student_id=conv.student_id)
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return {
        "id": new_conv.id,
        "teacher_id": new_conv.teacher_id,
        "student_id": new_conv.student_id,
        "created_at": new_conv.created_at,
        "student_username": student.username,
        "messages": [],
    }

@app.get("/conversations", response_model=list[ConversationResponse])
def get_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "teacher":
        conversations = db.query(Conversation).filter(Conversation.teacher_id == current_user.id).all()
    else:
        conversations = db.query(Conversation).filter(Conversation.student_id == current_user.id).all()

    # Enrich with student username
    result = []
    for conv in conversations:
        student = db.query(User).filter(User.id == conv.student_id).first()
        conv_dict = {
            "id": conv.id,
            "teacher_id": conv.teacher_id,
            "student_id": conv.student_id,
            "created_at": conv.created_at,
            "student_username": student.username if student else None,
            "messages": conv.messages,
        }
        result.append(conv_dict)
    return result

@app.post("/conversations/{conv_id}/messages", response_model=MessageResponse)
def send_message(conv_id: int, msg: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.id not in [conv.teacher_id, conv.student_id]:
        raise HTTPException(status_code=403, detail="Not authorized")
    new_msg = Message(conversation_id=conv_id, sender_id=current_user.id, content=msg.content)
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg

@app.get("/users", response_model=list[dict])
def get_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == "student").all()
    return [{"id": u.id, "username": u.username} for u in users]


# =====================================
# PREDICTION ENDPOINT
# =====================================
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        npimg = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        if frame is None:
            return {"error": "Invalid image"}

        prediction = predict_sign(frame)

        return {"prediction": prediction}

    except Exception as e:
        return {"error": str(e)}

@app.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
def get_messages(conv_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.conversation_id == conv_id).all()
    return messages