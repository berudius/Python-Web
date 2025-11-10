from pydantic import BaseModel
from typing import Optional

class UserUpdatePayload(BaseModel):
    trust_level: Optional[int] = None
    phone_number: Optional[str] = None