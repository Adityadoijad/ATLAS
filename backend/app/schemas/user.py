from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)

class UserCreate(UserBase):
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    google_id: Optional[str] = None

    class Config:
        from_attributes = True
