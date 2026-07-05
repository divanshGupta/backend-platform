import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserCreate(BaseModel):
    """What the client sends to create a user."""
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

class UserRead(BaseModel):
    """What the server sends back. Never includes hashed_password."""
    model_config =  ConfigDict(from_attributes=True) # without this pydantic v2 expects a dict like input and reject orm object.

    id: uuid.UUID
    email: str
    username: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

# i am not using regex based "must contain symbols etc" rules here, because of fast pace develope, it is necessary though and will implement later in v2
