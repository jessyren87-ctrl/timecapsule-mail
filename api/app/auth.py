from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(p: str) -> str:
    return pwd.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    return pwd.verify(p, hashed)

def create_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    return jwt.encode({"sub": user_id, "exp": exp}, settings.JWT_SECRET, algorithm="HS256")

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer()

def get_current_user(
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> User:
    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(User, sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
