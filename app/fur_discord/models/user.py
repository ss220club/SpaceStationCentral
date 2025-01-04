from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    #avatar: str
    #discriminator: str
    #public_flags: int
    #flags: int
    #banner: Any | None
    #global_name: str
    #avatar_decoration_data: Any | None
    #mfa_enabled: bool
    #clan: Any | None
    #locale: str
    #premium_type: int
