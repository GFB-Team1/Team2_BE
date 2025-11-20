from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    환경 변수 설정 클래스
    .env 파일에서 자동으로 값을 로드합니다.
    """
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 168
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
