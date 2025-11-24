from fastapi import APIRouter, HTTPException, status, Depends, Header
from database import supabase
from models import ContentSave, ContentResponse
from utils.auth import verify_token
from typing import Optional
import base64
from datetime import datetime

router = APIRouter(tags=["documents"])


async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    JWT 토큰 검증 의존성
    Authorization 헤더에서 Bearer 토큰을 추출하고 검증
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer 토큰이 필요합니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 인증 헤더 형식입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


@router.post("/room/{room_slug}/save-content", status_code=status.HTTP_200_OK)
async def save_content(
    room_slug: str,
    content_data: ContentSave,
    token_data = Depends(get_current_user)
):
    """
    방의 문서 내용 저장하기
    
    - **room_slug**: 방 슬러그
    - **content**: 저장할 문서 내용 (문자열)
    
    **인증 필요**: Authorization 헤더에 Bearer 토큰 필요
    
    Returns:
        - 성공 메시지
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
    
    # 2. 토큰의 room_id와 일치하는지 확인
    if token_data.room_id != room_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 방에 대한 접근 권한이 없습니다."
        )
    
    # 3. content를 bytea로 변환 (Base64 인코딩)
    try:
        # 문자열을 바이트로 변환 후 Base64 인코딩
        content_bytes = content_data.content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"콘텐츠 인코딩 중 오류가 발생했습니다: {str(e)}"
        )
    
    # 4. documents 테이블에 upsert
    try:
        # 기존 문서가 있는지 확인
        existing = (
            supabase
            .table("documents")
            .select("room_id")
            .eq("room_id", room_id)
            .execute()
        )
        
        if existing.data:
            # 업데이트
            result = (
                supabase
                .table("documents")
                .update({
                    "doc_state": content_base64,
                    "updated_at": datetime.utcnow().isoformat()
                })
                .eq("room_id", room_id)
                .execute()
            )
        else:
            # 새로 삽입
            result = (
                supabase
                .table("documents")
                .insert({
                    "room_id": room_id,
                    "doc_state": content_base64
                })
                .execute()
            )
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 저장에 실패했습니다."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 저장 중 오류가 발생했습니다: {str(e)}"
        )
    
    return {
        "message": "문서가 성공적으로 저장되었습니다.",
        "room_slug": room_slug,
        "saved_at": datetime.utcnow().isoformat()
    }


@router.get("/room/{room_slug}/content", response_model=ContentResponse)
async def get_content(
    room_slug: str,
    token_data = Depends(get_current_user)
):
    """
    방의 문서 내용 불러오기
    
    - **room_slug**: 방 슬러그
    
    **인증 필요**: Authorization 헤더에 Bearer 토큰 필요
    
    Returns:
        - **content**: 저장된 문서 내용
        - **updated_at**: 마지막 업데이트 시각
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
    
    # 2. 토큰의 room_id와 일치하는지 확인
    if token_data.room_id != room_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 방에 대한 접근 권한이 없습니다."
        )
    
    # 3. documents 테이블에서 문서 조회
    try:
        result = (
            supabase
            .table("documents")
            .select("doc_state, updated_at")
            .eq("room_id", room_id)
            .execute()
        )
        
        if not result.data:
            # 문서가 없으면 빈 내용 반환
            return ContentResponse(
                content=None,
                updated_at=None
            )
        
        doc = result.data[0]
        
        # 4. Base64 디코딩
        try:
            if doc.get("doc_state"):
                content_base64 = doc["doc_state"]
                content_bytes = base64.b64decode(content_base64)
                content = content_bytes.decode('utf-8')
            else:
                content = None
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"콘텐츠 디코딩 중 오류가 발생했습니다: {str(e)}"
            )
        
        # 5. updated_at 파싱
        updated_at_raw = doc.get("updated_at")
        try:
            if isinstance(updated_at_raw, str):
                updated_at = datetime.fromisoformat(
                    updated_at_raw.replace("Z", "+00:00")
                )
            else:
                updated_at = None
        except (ValueError, AttributeError):
            updated_at = None
        
        return ContentResponse(
            content=content,
            updated_at=updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서를 불러오는 중 오류가 발생했습니다: {str(e)}"
        )
