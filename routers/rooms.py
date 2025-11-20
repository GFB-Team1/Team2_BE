from fastapi import APIRouter, HTTPException, status
from database import supabase
from models import RoomCreate, RoomResponse, RoomInfo
import secrets
import string
from datetime import datetime

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
    room_slug = generate_room_slug()
    
    try:
        result = (
            supabase
            .table("rooms")
            .insert({
                "room_slug": room_slug,
                "title": room.title
                # created_at은 DB에서 자동 생성
            })
            .execute()
        )
    
        # 삽입 결과 확인
        if not result.data :
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="방 생성에 실패했습니다."
            )    
    except HTTPException:
        # 이미 발생한 HTTPException은 그대로 전파
        raise

    except Exception as e:
        # 모든 예상치 못한 에러 처리
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"방 생성 중 오류가 발생했습니다: {str(e)}"
        )    
    
    return RoomResponse(room_slug=room_slug)
    


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
    try:
        result = (
            supabase
            .table("rooms")
            .select("title, created_at")
            .eq("room_slug", room_slug)
            .execute()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"방 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
        )
        
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="방을 찾을 수 없습니다."
        )
    
    room = result.data[0]
    created_at_raw = room.get("created_at")

    # created_at 파싱
    try:
        if isinstance(created_at_raw, str):
            created_at = datetime.fromisoformat(
                created_at_raw.replace("Z", "+00:00")
            )
        else:
            created_at = datetime.utcnow()
    except (ValueError, AttributeError):
        created_at = datetime.utcnow()
    
    return RoomInfo(
        title=room["title"],
        created_at=created_at
    )