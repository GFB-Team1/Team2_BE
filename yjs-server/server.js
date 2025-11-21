require('dotenv').config()
const WebSocket = require('ws')
const http = require('http')
const { createClient } = require('@supabase/supabase-js')
const jwt = require('jsonwebtoken')

// Supabase 클라이언트 생성
const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_KEY
)

// JWT 설정
const JWT_SECRET = process.env.JWT_SECRET
if (!JWT_SECRET) {
    console.error('❌ JWT_SECRET이 설정되지 않았습니다!')
    process.exit(1)
}

// 방별 문서 저장소
const rooms = new Map()
// 구조: { "room_slug": { clients: Set(), updates: [] } }

const server = http.createServer((request, response) => {
    response.writeHead(200, { 'Content-Type': 'text/plain' })
    response.end('Y.js WebSocket Server Running')
})

const wss = new WebSocket.Server({ server })

// DB에서 문서 불러오기
async function loadDocumentFromDB(roomSlug) {
    try {
        // room_slug로 room_id 찾기
        const { data: roomData, error: roomError } = await supabase
            .from('rooms')
            .select('room_id')
            .eq('room_slug', roomSlug)
            .single()

        if (roomError || !roomData) {
            console.log(`[${roomSlug}] DB에 방 정보 없음`)
            return null
        }

        // documents 테이블에서 문서 상태 조회
        const { data: docData, error: docError } = await supabase
            .from('documents')
            .select('doc_state')
            .eq('room_id', roomData.room_id)
            .single()

        if (docError || !docData || !docData.doc_state) {
            console.log(`[${roomSlug}] DB에 문서 없음`)
            return null
        }

        // base64 디코딩
        const buffer = Buffer.from(docData.doc_state, 'base64')
        console.log(`[${roomSlug}] DB에서 문서 로드 완료 (${buffer.length} bytes)`)
        return buffer

    } catch (error) {
        console.error(`[${roomSlug}] DB 로드 실패:`, error)
        return null
    }
}

// DB에 문서 저장
async function saveDocumentToDB(roomSlug) {
    try {
        const room = rooms.get(roomSlug)
        if (!room || room.updates.length === 0) {
            console.log(`[${roomSlug}] 저장할 업데이트 없음`)
            return
        }

        // 모든 업데이트를 하나로 합치기
        const totalLength = room.updates.reduce((sum, update) => sum + update.length, 0)
        const merged = Buffer.concat(room.updates, totalLength)

        // room_slug로 room_id 찾기
        const { data: roomData, error: roomError } = await supabase
            .from('rooms')
            .select('room_id')
            .eq('room_slug', roomSlug)
            .single()

        if (roomError || !roomData) {
            console.error(`[${roomSlug}] 방 정보를 찾을 수 없음`)
            return
        }

        // base64 인코딩
        const encoded = merged.toString('base64')

        // upsert (있으면 업데이트, 없으면 생성)
        const { error: upsertError } = await supabase
            .from('documents')
            .upsert({
                room_id: roomData.room_id,
                doc_state: encoded
            })

        if (upsertError) {
            console.error(`[${roomSlug}] DB 저장 실패:`, upsertError)
        } else {
            console.log(`[${roomSlug}] DB 저장 완료 (${merged.length} bytes)`)
        }

    } catch (error) {
        console.error(`[${roomSlug}] DB 저장 중 오류:`, error)
    }
}

wss.on('connection', async (ws, req) => {
    // URL 파싱: ws://localhost:1234/room-slug?token=xxx
    const url = new URL(req.url, `ws://localhost:${PORT}`)
    const roomSlug = url.pathname.slice(1) // 맨 앞 '/' 제거
    const token = url.searchParams.get('token')

    console.log(`[${roomSlug}] 새 클라이언트 접속 시도`)

    // 1️⃣ 토큰 검증
    if (!token) {
        console.log(`[${roomSlug}] ❌ 토큰 없음 - 연결 거부`)
        ws.close(1008, '토큰이 필요합니다')
        return
    }

    let tokenData
    try {
        tokenData = jwt.verify(token, JWT_SECRET)
        console.log(`[${roomSlug}] ✅ 인증 성공: ${tokenData.nickname} (participant_id: ${tokenData.participant_id})`)
    } catch (error) {
        console.log(`[${roomSlug}] ❌ 토큰 검증 실패: ${error.message}`)
        ws.close(1008, '유효하지 않은 토큰')
        return
    }

    // 2️⃣ room_id 확인
    if (tokenData.room_id) {
        // 토큰의 room_id와 실제 방이 일치하는지 확인 (선택사항)
        const { data: roomData } = await supabase
            .from('rooms')
            .select('room_id')
            .eq('room_slug', roomSlug)
            .single()

        if (roomData && roomData.room_id !== tokenData.room_id) {
            console.log(`[${roomSlug}] ❌ 권한 없음 - 다른 방의 토큰`)
            ws.close(1008, '이 방에 접근할 권한이 없습니다')
            return
        }
    }

    // 3️⃣ 방 생성 및 문서 로드
    // 방이 없으면 생성 및 DB에서 문서 로드
    if (!rooms.has(roomSlug)) {
        rooms.set(roomSlug, {
            clients: new Set(),
            updates: []
        })

        // DB에서 문서 불러오기
        const savedDoc = await loadDocumentFromDB(roomSlug)
        if (savedDoc) {
            rooms.get(roomSlug).updates.push(savedDoc)
            // 첫 접속자에게 문서 전송
            ws.send(savedDoc)
        }
    } else {
        // 기존 방에 접속: 현재까지의 모든 업데이트 전송
        const room = rooms.get(roomSlug)
        room.updates.forEach(update => {
            ws.send(update)
        })
    }

    // 클라이언트 추가
    const room = rooms.get(roomSlug)
    room.clients.add(ws)
    console.log(`[${roomSlug}] 참가자 입장: ${tokenData.nickname} (현재 인원: ${room.clients.size}명)`)

    // 메시지 수신: 같은 방의 다른 모든 클라이언트에게 브로드캐스트
    ws.on('message', (message) => {
        const room = rooms.get(roomSlug)
        if (!room) return

        // 업데이트 저장 (메모리에 누적)
        room.updates.push(Buffer.from(message))

        // 다른 클라이언트에게 브로드캐스트
        room.clients.forEach((client) => {
            if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(message)
            }
        })
    })

    // 연결 종료
    ws.on('close', async () => {
        console.log(`[${roomSlug}] 클라이언트 연결 종료: ${tokenData.nickname}`)

        const room = rooms.get(roomSlug)
        if (room) {
            room.clients.delete(ws)
            const remaining = room.clients.size

            console.log(`[${roomSlug}] 남은 인원: ${remaining}명`)

            // 마지막 사람이 나갔을 때: DB에 저장
            if (remaining === 0) {
                await saveDocumentToDB(roomSlug)
                rooms.delete(roomSlug)
                console.log(`[${roomSlug}] 방 비어서 메모리 정리 완료`)
            }
        }
    })

    ws.on('error', (error) => {
        console.error(`[${roomSlug}] 웹소켓 에러:`, error)
    })
})

const PORT = process.env.PORT || 1234

server.listen(PORT, () => {
    console.log(`🚀 Y.js WebSocket Server running on ws://localhost:${PORT}`)
})