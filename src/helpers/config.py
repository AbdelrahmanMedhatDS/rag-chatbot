from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    
    APP_NAME : str
    APP_VERSION : str
    
    # file
    FILE_VALIDE_TYPES:List[str]
    FILE_MAX_SIZE:int
    MAX_CHUNK_SIZE:int


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

def get_settings():
    return Settings()