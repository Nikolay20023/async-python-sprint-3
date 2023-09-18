from pydantic import BaseSettings


class Setting(BaseSettings):
    host: str = '127.0.0.1'
    port: int = 8000

