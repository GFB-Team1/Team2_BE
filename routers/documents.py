from fastapi import APIRouter, HTTPException, status, Depends, Header
from database import supabase
from models import ContentSave, ContentResponse
from utils.auth import verify_token
from typing import Optional
import base64
from datetime import datetime
import json

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
    content_data: ContentSave
):
    """
    방의 문서 내용 저장하기
    
    - **room_slug**: 방 슬러그
    - **content**: 저장할 문서 내용 (문자열)
    
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
    
    # 3. content를 Base64 문자열로 그대로 저장
    # Supabase Python 클라이언트가 자동으로 bytea로 변환
    try:
        content_to_save = content_data.content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"콘텐츠 처리 중 오류가 발생했습니다: {str(e)}"
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
                    "doc_state": content_to_save,
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
                    "doc_state": content_to_save
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

@router.get("/room/{room_slug}/content/text")
async def get_content_as_text(
        room_slug: str
):
    """
    방의 문서 내용을 순수 텍스트로 불러오기 (Y.js 디코딩됨)

    - **room_slug**: 방 슬러그

    Returns:
        - **text**: 추출된 순수 텍스트
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

    # 2. documents 테이블에서 문서 조회
    try:
        result = (
            supabase
            .table("documents")
            .select("doc_state, updated_at")
            .eq("room_id", room_id)
            .execute()
        )

        if not result.data:
            return {
                "text": None,
                "updated_at": None
            }

        doc = result.data[0]

        # 3. doc_state 처리
        try:
            if doc.get("doc_state"):
                doc_state_raw = doc["doc_state"]

                # Hex escape 문자열을 bytes로 변환
                if isinstance(doc_state_raw, str) and doc_state_raw.startswith('\\x'):
                    hex_string = doc_state_raw[2:]
                    doc_bytes = bytes.fromhex(hex_string)

                    if len(doc_bytes) > 0 and doc_bytes[0] == 0:
                        base64_content = base64.b64encode(doc_bytes).decode('utf-8')
                    else:
                        base64_content = doc_bytes.decode('utf-8')

                elif isinstance(doc_state_raw, bytes):
                    base64_content = base64.b64encode(doc_state_raw).decode('utf-8')
                else:
                    base64_content = doc_state_raw

                # Base64 → bytes
                yjs_bytes = base64.b64decode(base64_content)

                # 간단한 텍스트 추출 (printable ASCII만)
                text_content = ""
                for byte in yjs_bytes:
                    # printable ASCII + 줄바꿈, 탭, 한글 범위
                    if 32 <= byte <= 126 or byte in [9, 10, 13] or byte >= 128:
                        text_content += chr(byte)

                text = text_content.strip() if text_content.strip() else None

            else:
                text = None
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"텍스트 추출 중 오류가 발생했습니다: {str(e)}"
            )

        # 4. updated_at 파싱
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

        return {
            "text": text,
            "updated_at": updated_at
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서를 불러오는 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/room/{room_slug}/content", response_model=ContentResponse)
async def get_content(
    room_slug: str
):
    """
    방의 문서 내용 불러오기
    
    - **room_slug**: 방 슬러그
    
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
        
        # 4. doc_state 처리
        # Supabase Python 클라이언트는 bytea를 hex escape 문자열로 반환함 (\x...)
        try:
            if doc.get("doc_state"):
                doc_state_raw = doc["doc_state"]
                
                # Hex escape 문자열을 bytes로 변환
                if isinstance(doc_state_raw, str) and doc_state_raw.startswith('\\x'):
                    hex_string = doc_state_raw[2:]
                    doc_bytes = bytes.fromhex(hex_string)
                    
                    if len(doc_bytes) > 0 and doc_bytes[0] == 0:
                        content = base64.b64encode(doc_bytes).decode('utf-8')
                    else:
                        content = doc_bytes.decode('utf-8')
                    
                elif isinstance(doc_state_raw, bytes):
                    content = base64.b64encode(doc_state_raw).decode('utf-8')
                else:
                    content = doc_state_raw
            else:
                content = None
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"콘텐츠 처리 중 오류가 발생했습니다: {str(e)}"
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


