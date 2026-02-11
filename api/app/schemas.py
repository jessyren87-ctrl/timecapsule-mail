from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    timezone: str = "America/Los_Angeles"

class LoginReq(BaseModel):
    email: EmailStr
    password: str

class AuthResp(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MeResp(BaseModel):
    email: EmailStr
    timezone: str

class CreateLetterReq(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    minDays: int = Field(ge=1, le=3650)
    maxDays: int = Field(ge=1, le=3650)

class LetterResp(BaseModel):
    id: str
    subject: str
    body: str
    sendAtUtc: datetime
    status: str
    createdAt: datetime
