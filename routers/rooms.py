from fastapi import APIRouter, HTTPException, status
from database import supabase
from models import RoomCreate, RoomResponse, RoomInfo
import secrets
import string

router = APIRouter(tags=["rooms"])


def generate_room_slug(length: int = 9) -> str:
    """
    고유한 방 슬러그 생성 함수
    예: "kdef-39a1"
    """
    chars = string.ascii_lowercase + string.digits
    slug = ''.join(secrets.choice(chars) for _ in range(length))
    # 중간에 하이픈 추가 (가독성)
    return f"{slug[:4]}-{slug[4:]}"


@router.post("/create-room", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(room: RoomCreate):
    """
    새 방(약속) 만들기
    
    - **title**: 방 제목 (필수, 1~255자)
    
    Returns:
        - **room_slug**: 생성된 방의 고유 슬러그 (예: "kdef-39a1")
    """
    # TODO: 여기서 구현하세요!
    # 1. generate_room_slug()로 고유한 슬러그 생성
    # 2. supabase.table("rooms").insert() 사용해서 DB에 저장
    # 3. 생성된 room_slug 반환
    
    pass


@router.get("/room/{room_slug}", response_model=RoomInfo)
async def get_room(room_slug: str):
    """
    방 존재 여부 확인 및 방 정보 가져오기
    
    - **room_slug**: 방 슬러그 (예: "kdef-39a1")
    
    Returns:
        - **title**: 방 제목
        - **created_at**: 방 생성 일시
    
    Raises:
        - **404**: 방을 찾을 수 없음
    """
    # TODO: 여기서 구현하세요!
    # 1. supabase.table("rooms").select().eq("room_slug", room_slug) 사용
    # 2. 방이 없으면 404 에러 발생
    # 3. 방 정보(title, created_at) 반환
    
    pass
