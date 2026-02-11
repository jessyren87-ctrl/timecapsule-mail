from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from .letter_models import Letter
from .random_time import pick_random_send_at_utc

from .db import engine, get_db, Base
from .models import User
from .schemas import RegisterReq, LoginReq, AuthResp, MeResp, CreateLetterReq, LetterResp
from .auth import hash_password, verify_password, create_token, get_current_user

app = FastAPI(title="TimeCapsule API")

# MVP: 启动时建表（上线建议用 Alembic migration）
# Base.metadata.create_all(bind=engine)

import time
from sqlalchemy import text

@app.on_event("startup")
def on_startup():
    # 等数据库 ready（最多等 ~30 秒）
    for i in range(30):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as e:
            print(f"[startup] db not ready yet ({i+1}/30): {e}")
            time.sleep(1)

    # 再建表
    Base.metadata.create_all(bind=engine)
    print("[startup] db ready, tables ensured")


@app.get("/health")
def health():
    return {"ok": True}

@app.post("/auth/register", response_model=AuthResp)
def register(req: RegisterReq, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == req.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    u = User(
        email=req.email,
        password_hash=hash_password(req.password),
        timezone=req.timezone,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return AuthResp(access_token=create_token(str(u.id)))

@app.post("/auth/login", response_model=AuthResp)
def login(req: LoginReq, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == req.email).first()
    if not u or not verify_password(req.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthResp(access_token=create_token(str(u.id)))

@app.get("/me", response_model=MeResp)
def me(user: User = Depends(get_current_user)):
    return MeResp(email=user.email, timezone=user.timezone)

from sqlalchemy import text

@app.post("/debug/letters/{letter_id}/send_in_minutes")
def debug_send_in_minutes(letter_id: str, minutes: int = 1, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 只允许修改自己的信
    row = db.execute(
        text("SELECT id FROM letters WHERE id=:id AND user_id=:uid"),
        {"id": letter_id, "uid": str(user.id)},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Letter not found")

    db.execute(
        text("""
            UPDATE letters
            SET send_at_utc = (NOW() AT TIME ZONE 'UTC') + (:m || ' minutes')::interval,
                status='Scheduled'
            WHERE id=:id
        """),
        {"id": letter_id, "m": minutes},
    )
    db.commit()
    return {"ok": True, "send_in_minutes": minutes}


@app.post("/letters", response_model=LetterResp)
def create_letter(req: CreateLetterReq, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if req.maxDays < req.minDays:
        raise HTTPException(status_code=400, detail="maxDays must be >= minDays")

    now_utc = datetime.now(timezone.utc)
    send_at_utc = pick_random_send_at_utc(
        now_utc=now_utc,
        user_tz=user.timezone,
        min_days=req.minDays,
        max_days=req.maxDays,
    )

    letter = Letter(
        user_id=user.id,
        subject=req.subject,
        body=req.body,
        send_at_utc=send_at_utc,
        status="Scheduled",
    )
    db.add(letter)
    db.commit()
    db.refresh(letter)

    return LetterResp(
        id=str(letter.id),
        subject=letter.subject,
        body=letter.body,
        sendAtUtc=letter.send_at_utc,
        status=letter.status,
        createdAt=letter.created_at,
    )


@app.get("/letters", response_model=list[LetterResp])
def list_letters(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    letters = (
        db.query(Letter)
        .filter(Letter.user_id == user.id)
        .order_by(Letter.created_at.desc())
        .all()
    )

    return [
        LetterResp(
            id=str(l.id),
            subject=l.subject,
            body=l.body,
            sendAtUtc=l.send_at_utc,
            status=l.status,
            createdAt=l.created_at,
        )
        for l in letters
    ]
