from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from utils.auth import verify_token
import websockets
import asyncio
import logging

router = APIRouter(tags=["websocket"])

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Node.js Y.js 서버 주소
YSERVER_URL = "ws://localhost:1234"


@router.websocket("/ws/{room_slug}")
async def websocket_proxy(
    websocket: WebSocket,
    room_slug: str,
    token: str = Query(..., description="JWT 인증 토큰")
):
    """
    Y.js 웹소켓 프록시 엔드포인트
    
    FastAPI가 클라이언트와 Node.js Y.js 서버 사이를 중계합니다.
    
    - **room_slug**: 방 고유 슬러그
    - **token**: JWT 인증 토큰 (쿼리 파라미터)
    
    **연결 순서:**
    1. 클라이언트 → FastAPI WebSocket
    2. FastAPI가 JWT 토큰 검증
    3. FastAPI → Node.js Y.js 서버 연결
    4. 양방향 메시지 중계
    """
    
    # 디버그 로그
    logger.info(f"[{room_slug}] WebSocket 연결 시도")
    logger.info(f"[{room_slug}] 토큰 앞 50자: {token[:50]}...")
    
    # 1. JWT 토큰 검증
    try:
        token_data = verify_token(token)
        logger.info(f"[{room_slug}] 사용자 인증 성공: {token_data.nickname}")
    except HTTPException as e:
        logger.error(f"[{room_slug}] 인증 실패 - HTTPException: {e.detail}")
        await websocket.close(code=1008, reason=str(e.detail))
        return
    except Exception as e:
        logger.error(f"[{room_slug}] 인증 실패 - Exception: {type(e).__name__}: {str(e)}")
        await websocket.close(code=1008, reason="인증 실패")
        return
    
    # 2. 클라이언트 WebSocket 연결 수락
    await websocket.accept()
    logger.info(f"[{room_slug}] 클라이언트 연결 수락: {token_data.nickname}")
    
    # 3. Node.js Y.js 서버에 연결
    yjs_url = f"{YSERVER_URL}/{room_slug}"
    
    try:
        async with websockets.connect(yjs_url) as yjs_ws:
            logger.info(f"[{room_slug}] Y.js 서버 연결 성공")
            
            # 4. 양방향 메시지 중계
            async def client_to_yjs():
                """클라이언트 → Y.js 서버"""
                try:
                    while True:
                        # 클라이언트에서 메시지 수신
                        data = await websocket.receive_bytes()
                        # Y.js 서버로 전송
                        await yjs_ws.send(data)
                except WebSocketDisconnect:
                    logger.info(f"[{room_slug}] 클라이언트 연결 종료: {token_data.nickname}")
                    await yjs_ws.close()
                except Exception as e:
                    logger.error(f"[{room_slug}] client_to_yjs 에러: {e}")
            
            async def yjs_to_client():
                """Y.js 서버 → 클라이언트"""
                try:
                    while True:
                        # Y.js 서버에서 메시지 수신
                        data = await yjs_ws.recv()
                        # 클라이언트로 전송
                        await websocket.send_bytes(data)
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"[{room_slug}] Y.js 서버 연결 종료")
                except Exception as e:
                    logger.error(f"[{room_slug}] yjs_to_client 에러: {e}")
            
            # 두 작업 동시 실행
            await asyncio.gather(
                client_to_yjs(),
                yjs_to_client()
            )
    
    except Exception as e:
        logger.error(f"[{room_slug}] Y.js 서버 연결 실패: {e}")
        await websocket.close(code=1011, reason="Y.js 서버 연결 실패")
    
    finally:
        logger.info(f"[{room_slug}] 프록시 연결 종료: {token_data.nickname}")
