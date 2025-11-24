# 🔌 WebSocket 연결 가이드 (프론트엔드용)

## 📋 개요

이 프로젝트는 **Y.js**를 사용한 실시간 협업 에디터를 제공합니다.
프론트엔드는 **Node.js Y.js 서버**에 직접 WebSocket으로 연결합니다.

---

## 🌐 WebSocket 서버 정보

### 기본 연결 정보
```
서버 주소: ws://localhost:1234
프로토콜: WebSocket
인증 방식: JWT 토큰 (쿼리 파라미터)
```

### 연결 URL 형식
```
ws://localhost:1234/{room_slug}?token={jwt_token}
```

**예시:**
```
ws://localhost:1234/kdef-39a1?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🔐 인증 흐름

### 1️⃣ 방 참가 API 호출하여 JWT 토큰 획득

**엔드포인트:**
```http
POST http://localhost:8000/room/{room_slug}/join
Content-Type: application/json

{
  "nickname": "사용자닉네임",
  "password": "1234"
}
```

**응답:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "nickname": "사용자닉네임"
}
```

### 2️⃣ 받은 토큰으로 WebSocket 연결

```javascript
const roomSlug = "kdef-39a1"
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

const wsUrl = `ws://localhost:1234/${roomSlug}?token=${token}`
const ws = new WebSocket(wsUrl)
```

---

## 💻 프론트엔드 구현 예시

### 📦 필요한 패키지

```bash
npm install yjs y-websocket
```

### 🎯 Y.js 연결 코드 (React 예시)

```javascript
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'

function CollaborativeEditor({ roomSlug, token }) {
  const [yDoc, setYDoc] = useState(null)
  const [provider, setProvider] = useState(null)

  useEffect(() => {
    // Y.js 문서 생성
    const doc = new Y.Doc()
    
    // WebSocket Provider 연결
    const wsProvider = new WebsocketProvider(
      'ws://localhost:1234',  // 서버 주소
      roomSlug,               // 방 슬러그
      doc,                    // Y.js 문서
      {
        params: { token }     // JWT 토큰
      }
    )

    // 연결 상태 이벤트
    wsProvider.on('status', event => {
      console.log('WebSocket 상태:', event.status) // 'connecting', 'connected', 'disconnected'
    })

    wsProvider.on('sync', isSynced => {
      console.log('동기화 완료:', isSynced)
    })

    setYDoc(doc)
    setProvider(wsProvider)

    // 정리
    return () => {
      wsProvider.disconnect()
      doc.destroy()
    }
  }, [roomSlug, token])

  return (
    <div>
      {/* 여기서 yDoc을 사용하여 에디터 구현 */}
    </div>
  )
}
```

### 🖊️ Tiptap 에디터와 연동 예시

```javascript
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Collaboration from '@tiptap/extension-collaboration'
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'

function TiptapCollaborativeEditor({ roomSlug, token }) {
  const [provider, setProvider] = useState(null)

  useEffect(() => {
    const doc = new Y.Doc()
    const wsProvider = new WebsocketProvider(
      'ws://localhost:1234',
      roomSlug,
      doc,
      { params: { token } }
    )
    
    setProvider(wsProvider)

    return () => {
      wsProvider.disconnect()
      doc.destroy()
    }
  }, [roomSlug, token])

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        history: false, // Y.js가 히스토리 관리
      }),
      Collaboration.configure({
        document: provider?.document,
      }),
    ],
    content: '<p>협업 문서를 시작하세요!</p>',
  })

  return <EditorContent editor={editor} />
}
```

---

## 🔄 연결 상태 처리

### WebSocket 상태

| 상태 | 설명 |
|------|------|
| `connecting` | 서버에 연결 시도 중 |
| `connected` | 서버 연결 완료 |
| `disconnected` | 연결 끊김 (자동 재연결 시도) |

### 에러 처리

```javascript
wsProvider.on('connection-close', event => {
  console.error('연결 종료:', event)
  
  if (event.code === 1008) {
    alert('인증 실패: 토큰이 유효하지 않습니다.')
  }
})

wsProvider.on('connection-error', error => {
  console.error('연결 에러:', error)
})
```

---

## 🧪 테스트 방법

### 1. 백엔드 서버 실행
```bash
# FastAPI 서버
cd Team2_BE
python main.py

# Node.js Y.js 서버
cd yjs-server
npm install
node server.js
```

### 2. 방 생성 및 참가
```bash
# 1. 방 생성
curl -X POST http://localhost:8000/create-room \
  -H "Content-Type: application/json" \
  -d '{"title": "테스트 방"}'

# 응답: {"room_slug": "kdef-39a1"}

# 2. 방 참가 (토큰 받기)
curl -X POST http://localhost:8000/room/kdef-39a1/join \
  -H "Content-Type: application/json" \
  -d '{"nickname": "철수", "password": "1234"}'

# 응답: {"token": "eyJhbG...", "nickname": "철수"}
```

### 3. WebSocket 연결 테스트 (Chrome DevTools)
```javascript
// 브라우저 콘솔에서 테스트
const token = "여기에_받은_토큰_붙여넣기"
const ws = new WebSocket(`ws://localhost:1234/kdef-39a1?token=${token}`)

ws.onopen = () => console.log('✅ 연결 성공')
ws.onmessage = (e) => console.log('📨 메시지:', e.data)
ws.onerror = (e) => console.error('❌ 에러:', e)
ws.onclose = (e) => console.log('🔌 연결 종료:', e.code, e.reason)
```

---

## 🚨 주의사항

### 1. 토큰 유효기간
- JWT 토큰은 **24시간** 유효
- 만료 시 재로그인 필요 (방 참가 API 재호출)

### 2. CORS 설정
- 개발 환경: `ws://localhost:1234` 사용
- 프로덕션: 실제 도메인으로 변경 필요

### 3. 네트워크 재연결
- Y.js는 자동 재연결 지원
- 단, 토큰 만료 시 수동 재연결 필요

### 4. 문서 저장
- 마지막 사용자가 나갈 때 **자동 저장**
- 수동 저장 API: `POST /room/{room_slug}/save-content`

---

## 📚 관련 문서

- [Y.js 공식 문서](https://docs.yjs.dev/)
- [y-websocket Provider](https://github.com/yjs/y-websocket)
- [Tiptap Collaboration](https://tiptap.dev/docs/editor/extensions/functionality/collaboration)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)

---

## 🆘 문제 해결

### 연결이 안 될 때
1. Node.js 서버가 실행 중인지 확인 (`ws://localhost:1234`)
2. 토큰이 유효한지 확인
3. 방 슬러그가 올바른지 확인

### 인증 실패 (1008 에러)
- 토큰이 만료되었거나 유효하지 않음
- 방 참가 API를 다시 호출하여 새 토큰 획득

### 문서가 동기화되지 않을 때
- 네트워크 연결 확인
- 브라우저 콘솔에서 WebSocket 상태 확인
- `wsProvider.on('sync')` 이벤트 모니터링

---

**문의사항이 있으면 백엔드 팀에게 연락주세요!** 🚀
