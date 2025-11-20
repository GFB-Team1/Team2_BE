from fastapi import APIRouter, HTTPException, status
from database import supabase
from models import RoomCreate, RoomResponse, RoomInfo, ParticipantJoin, ParticipantResponse  # ← 2개 추가
from utils.auth import hash_password, verify_password, create_access_token  # ← 새 줄 추가
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

@router.post("/room/{room_slug}/join", response_model=ParticipantResponse)
async def join_room(room_slug: str, participant: ParticipantJoin):
    """
    방에 참가하기 (신규 등록 또는 로그인)

    password는 최소 4자리 이상
    """

    # 1. room_slug로 room_id 찾기
    try:
        room_result = (
            supabase
            .table("rooms")
            .select("room_id")
            .eq("room_slug", room_slug)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"방 정보를 조회하는 중 오류가 발생했습니다: {str(e)}"
        )

    if not room_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="방을 찾을 수 없습니다."
        )

    room_id = room_result.data[0]["room_id"]

    # 2. 기존 참가자 확인
    try:
        participant_result = (
            supabase
            .table("participants")
            .select("participant_id, password_hash")
            .eq("room_id", room_id)
            .eq("nickname", participant.nickname)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"참가자 정보를 조회하는 중 오류가 발생했습니다: {str(e)}"
        )

    # 3-A. 기존 참가자 (로그인)
    if participant_result.data:
        existing = participant_result.data[0]

        if not verify_password(participant.password, existing["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비밀번호가 일치하지 않습니다."
            )

        participant_id = existing["participant_id"]

    # 3-B. 신규 참가자 (회원가입)
    else:
        hashed_password = hash_password(participant.password)

        try:
            insert_result = (
                supabase
                .table("participants")
                .insert({
                    "room_id": room_id,
                    "nickname": participant.nickname,
                    "password_hash": hashed_password
                })
                .execute()
            )

            if not insert_result.data or len(insert_result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="참가자 등록에 실패했습니다."
                )

            participant_id = insert_result.data[0]["participant_id"]

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"참가자 등록 중 오류가 발생했습니다: {str(e)}"
            )

    # 4. JWT 토큰 생성
    token = create_access_token({
        "room_id": room_id,
        "participant_id": participant_id,
        "nickname": participant.nickname
    })

    return ParticipantResponse(
        token=token,
        nickname=participant.nickname
    )
