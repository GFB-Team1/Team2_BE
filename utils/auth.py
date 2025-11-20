from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings
from models import TokenData
from fastapi import HTTPException, status

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """비밀번호를 bcrypt로 해싱합니다."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시를 비교합니다."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data : dict) -> str :
    """JWT 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """JWT 토큰을 검증하고 페이로드를 반환합니다."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        room_id: int = payload.get("room_id")
        participant_id: int = payload.get("participant_id")
        nickname: str = payload.get("nickname")

        if room_id is None or participant_id is None or nickname is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰 페이로드가 유효하지 않습니다."
            )

        return TokenData(
            room_id=room_id,
            participant_id=participant_id,
            nickname=nickname
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않습니다."
        )