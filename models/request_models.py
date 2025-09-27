from pydantic import BaseModel

class LoginRequest(BaseModel):
    name: str
