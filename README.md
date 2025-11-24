# 🗓️ Meeting Scheduler API

실시간 협업 일정 조율 서비스 백엔드

## 📌 프로젝트 개요

여러 사람이 동시에 협업하며 일정을 조율할 수 있는 실시간 협업 문서 서비스입니다.
- **FastAPI** 기반 REST API
- **Y.js** 기반 실시간 협업 에디터
- **Supabase** 데이터베이스
- **WebSocket** 실시간 통신

---

## 🏗️ 아키텍처

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│             │  HTTP   │              │  REST   │             │
│  Frontend   ├────────►│   FastAPI    ├────────►│  Supabase   │
│             │         │  (Port 8000) │         │  (Database) │
│             │         └──────────────┘         └─────────────┘
│             │
│             │  WebSocket
│             ├────────►┌──────────────┐
│             │         │   Node.js    │
└─────────────┘         │ Y.js Server  │
                        │ (Port 1234)  │
                        └──────────────┘
```

---

## 🚀 시작하기

### 1️⃣ 환경 설정

**.env 파일 생성** (프로젝트 루트)
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
JWT_SECRET=your_secret_key_at_least_32_characters
```

**yjs-server/.env 파일 생성**
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
JWT_SECRET=your_secret_key_at_least_32_characters
PORT=1234
```

### 2️⃣ 의존성 설치

**Python (FastAPI)**
```bash
pip install -r requirements.txt
```

**Node.js (Y.js 서버)**
```bash
cd yjs-server
npm install
```

### 3️⃣ 서버 실행

**FastAPI 서버**
```bash
python main.py
# 또는
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Y.js WebSocket 서버**
```bash
cd yjs-server
node server.js
```

### 4️⃣ 서버 확인

- **FastAPI**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **Y.js 서버**: ws://localhost:1234

---

## 📡 API 명세

### 🏠 기본 정보

**Base URL:** `http://localhost:8000`

**인증 방식:** JWT Bearer Token (방 참가 후 획득)

---

## 📋 API 엔드포인트

### 1. 방(Room) 관리

#### 1.1 방 생성

```http
POST /create-room
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "2024년 1월 모임 일정 조율"
}
```

**Response (201):**
```json
{
  "room_slug": "kdef-39a1"
}
```

**설명:**
- 새로운 협업 방을 생성합니다.
- `room_slug`는 고유한 9자리 식별자입니다.

---

#### 1.2 방 정보 조회

```http
GET /room/{room_slug}
```

**Path Parameters:**
- `room_slug`: 방 고유 슬러그 (예: "kdef-39a1")

**Response (200):**
```json
{
  "title": "2024년 1월 모임 일정 조율",
  "created_at": "2024-11-24T10:30:00Z"
}
```

**Error (404):**
```json
{
  "detail": "방을 찾을 수 없습니다."
}
```

---

#### 1.3 방 참가하기

```http
POST /room/{room_slug}/join
Content-Type: application/json
```

**Request Body:**
```json
{
  "nickname": "김철수",
  "password": "1234"
}
```

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "nickname": "김철수"
}
```

**설명:**
- 신규 참가: 닉네임과 비밀번호로 새 계정 생성
- 재참가: 기존 닉네임과 비밀번호로 로그인
- 받은 `token`은 WebSocket 연결 및 문서 API에 사용

**주의사항:**
- 같은 방에서 닉네임 중복 불가
- 비밀번호는 최소 4자 이상

---

### 2. 문서(Document) 관리

#### 2.1 문서 내용 저장

```http
POST /room/{room_slug}/save-content
Content-Type: application/json
```

**Request Body:**
```json
{
  "content": "Base64로 인코딩된 Y.js 문서 상태"
}
```

**Response (200):**
```json
{
  "message": "문서가 성공적으로 저장되었습니다.",
  "room_slug": "kdef-39a1",
  "saved_at": "2024-11-24T10:35:00Z"
}
```

**설명:**
- Y.js 문서 상태를 DB에 저장합니다.
- 보통 자동 저장되지만, 수동 저장이 필요할 때 사용합니다.

---

#### 2.2 문서 내용 불러오기 (Y.js 형식)

```http
GET /room/{room_slug}/content
```

**Response (200):**
```json
{
  "content": "Base64로 인코딩된 Y.js 문서 상태",
  "updated_at": "2024-11-24T10:35:00Z"
}
```

**Response (200) - 문서 없음:**
```json
{
  "content": null,
  "updated_at": null
}
```

**설명:**
- Y.js가 읽을 수 있는 형식의 문서 상태를 반환합니다.

---

#### 2.3 문서 내용 불러오기 (텍스트 형식)

```http
GET /room/{room_slug}/content/text
```

**Response (200):**
```json
{
  "text": "안녕하세요\n여기는 협업 문서입니다.",
  "updated_at": "2024-11-24T10:35:00Z"
}
```

**설명:**
- Y.js 바이너리를 텍스트로 변환하여 반환합니다.
- 프리뷰나 검색 등에 활용할 수 있습니다.

---

### 3. WebSocket (실시간 협업)

#### 3.1 Y.js WebSocket 연결

```
ws://localhost:1234/{room_slug}?token={jwt_token}
```

**Parameters:**
- `room_slug`: 방 고유 슬러그
- `token`: JWT 인증 토큰 (방 참가 API에서 획득)

**예시:**
```
ws://localhost:1234/kdef-39a1?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**상세 가이드:** [WEBSOCKET_GUIDE.md](./WEBSOCKET_GUIDE.md) 참고

---

## 🗄️ 데이터베이스 스키마

### `rooms` 테이블
```sql
- room_id (integer, PRIMARY KEY)
- room_slug (text, UNIQUE)
- title (varchar(255))
- created_at (timestamp)
```

### `participants` 테이블
```sql
- participant_id (integer, PRIMARY KEY)
- room_id (integer, FOREIGN KEY)
- nickname (varchar(50))
- password_hash (text)
- joined_at (timestamp)
- UNIQUE(room_id, nickname)
```

### `documents` 테이블
```sql
- room_id (integer, PRIMARY KEY, FOREIGN KEY)
- doc_state (bytea)
- updated_at (timestamp)
```

---

## 🧪 API 테스트 예시

### cURL로 전체 플로우 테스트

```bash
# 1. 방 생성
curl -X POST http://localhost:8000/create-room \
  -H "Content-Type: application/json" \
  -d '{"title": "테스트 방"}'

# 응답: {"room_slug": "kdef-39a1"}

# 2. 방 정보 조회
curl http://localhost:8000/room/kdef-39a1

# 3. 방 참가 (첫 번째 사용자)
curl -X POST http://localhost:8000/room/kdef-39a1/join \
  -H "Content-Type: application/json" \
  -d '{"nickname": "철수", "password": "1234"}'

# 응답: {"token": "eyJ...", "nickname": "철수"}

# 4. 방 참가 (두 번째 사용자)
curl -X POST http://localhost:8000/room/kdef-39a1/join \
  -H "Content-Type: application/json" \
  -d '{"nickname": "영희", "password": "5678"}'

# 5. 문서 내용 조회
curl http://localhost:8000/room/kdef-39a1/content/text
```

### Postman 컬렉션

Swagger UI에서 **"Try it out"** 버튼으로 직접 테스트할 수 있습니다.
👉 http://localhost:8000/docs

---

## 📦 의존성

### Python (requirements.txt)
```
fastapi
uvicorn[standard]
supabase
python-dotenv
python-jose[cryptography]
passlib[bcrypt]
pydantic
```

### Node.js (package.json)
```
ws
@supabase/supabase-js
jsonwebtoken
dotenv
y-websocket
yjs
```

---

## 🔒 보안 고려사항

### JWT 토큰
- 만료 시간: 24시간
- Secret Key는 최소 32자 이상 권장
- 프로덕션에서는 환경변수로 관리

### 비밀번호
- bcrypt 해싱 사용
- 최소 4자 이상 (프로덕션에서는 더 강력한 정책 권장)

### CORS
- 개발 환경: 모든 origin 허용 (`*`)
- 프로덕션: 특정 도메인만 허용하도록 수정 필요

---

## 🐛 문제 해결

### 서버 실행 안 됨
```bash
# Python 가상환경 활성화 확인
pip list

# 의존성 재설치
pip install -r requirements.txt
```

### WebSocket 연결 안 됨
```bash
# Y.js 서버 실행 확인
cd yjs-server
node server.js

# 포트 확인
netstat -ano | findstr :1234  # Windows
lsof -i :1234                  # Mac/Linux
```

### 토큰 인증 실패
- JWT_SECRET이 FastAPI와 Node.js 서버에서 동일한지 확인
- 토큰 만료 여부 확인 (24시간)
- 방 참가 API를 다시 호출하여 새 토큰 획득

---

## 📚 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Y.js 공식 문서](https://docs.yjs.dev/)
- [Supabase 공식 문서](https://supabase.com/docs)
- [WebSocket 프론트엔드 가이드](./WEBSOCKET_GUIDE.md)

---

## 👥 팀 정보

**프로젝트명:** Team2_BE  
**버전:** 1.0.0  
**설명:** 실시간 협업 일정 조율 서비스 백엔드

---

## 📄 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

---

**문의사항이나 버그 리포트는 이슈로 등록해주세요!** 🚀
