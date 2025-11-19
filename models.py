from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# === 방(Room) 관련 모델 ===

class RoomCreate(BaseModel):
    """방 생성 요청 모델"""
    title: str = Field(..., min_length=1, max_length=255, description="방 제목")


class RoomResponse(BaseModel):
    """방 생성 응답 모델"""
    room_slug: str = Field(..., description="생성된 방의 고유 슬러그")


class RoomInfo(BaseModel):
    """방 정보 조회 응답 모델"""
    title: str
    created_at: datetime


# === 참가자(Participant) 관련 모델 ===

class ParticipantJoin(BaseModel):
    """참가자 입장 요청 모델"""
    nickname: str = Field(..., min_length=1, max_length=50, description="참가자 닉네임")
    password: str = Field(..., min_length=4, description="비밀번호")


class ParticipantResponse(BaseModel):
    """참가자 입장 응답 모델"""
    token: str = Field(..., description="JWT 인증 토큰")
    nickname: str = Field(..., description="참가자 닉네임")


# === 내부용 모델 ===

class TokenData(BaseModel):
    """JWT 토큰 페이로드 모델"""
    room_id: int
    participant_id: int
    nickname: str
