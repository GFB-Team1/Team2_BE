from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import rooms
# websocket 프록시 제거 - 클라이언트가 Node.js에 직접 연결

app = FastAPI(
    title="Meeting Scheduler API",
    description="실시간 협업 일정 조율 서비스 백엔드",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연동을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(rooms.router)
# app.include_router(websocket.router)  # 프록시 제거


@app.get("/")
def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Meeting Scheduler API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
