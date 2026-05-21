# 🚄 KTX 취소표 알림 텔레그램 봇

GitHub Actions로 5분마다 자동 실행되어 KTX 취소표가 생기면 텔레그램으로 알려줍니다.

---

## ⚙️ 설정 방법 (5단계)

### 1단계 — GitHub 저장소 만들기
1. [github.com](https://github.com) 에서 **New repository** 클릭
2. 이름 입력 (예: `ktx-alert`) → **Create repository**
3. 이 폴더의 파일을 전부 업로드

```bash
git init
git add .
git commit -m "KTX 취소표 알림 봇"
git remote add origin https://github.com/본인아이디/ktx-alert.git
git push -u origin main
```

---

### 2단계 — 텔레그램 봇 만들기
1. 텔레그램에서 **@BotFather** 검색 → `/newbot`
2. 봇 이름 입력 → **API Token** 복사해두기 (예: `123456:ABCdef...`)
3. 봇과 대화 시작: 봇 검색 후 `/start` 전송
4. Chat ID 확인:
   ```
   https://api.telegram.org/bot<토큰>/getUpdates
   ```
   → `"chat":{"id": 1234567890}` 에서 숫자 복사

---

### 3단계 — GitHub Secrets 등록
저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 값 |
|---|---|
| `KORAIL_ID` | 코레일 아이디 |
| `KORAIL_PW` | 코레일 비밀번호 |
| `TELEGRAM_TOKEN` | BotFather에서 받은 토큰 |
| `TELEGRAM_CHAT_ID` | 위에서 확인한 Chat ID |

---

### 4단계 — 검색 조건 수정
`.github/workflows/ktx-alert.yml` 파일에서 아래 부분 수정:

```yaml
DEPARTURE: "부산"      # 출발역
ARRIVAL:   "서울"      # 도착역
DATE:      "20250601"  # 날짜 (YYYYMMDD)
DEP_TIME:  "000000"    # 이 시각 이후 열차 (예: "080000" = 8시 이후)
```

**지원 역 목록:**
서울, 용산, 영등포, 수원, 천안아산, 오송, 대전, 김천구미,
동대구, 경주, 울산, 부산, 광명, 공주, 익산, 정읍, 광주송정, 나주, 목포

---

### 5단계 — 활성화 확인
- 저장소 → **Actions** 탭 → `KTX 취소표 알림` 워크플로우 확인
- **Run workflow** 버튼으로 즉시 테스트 가능
- 이후 매 5분 자동 실행

---

## 📱 알림 예시

```
🚄 KTX 취소표 알림
📍 부산 → 서울
📅 2025-06-01
🕐 확인 시각: 14:30:05
────────────────────────────

🚅 KTX 101호  07:30 → 10:10
   일반실: ✅ 예매가능
   특  실: ❌ 매진
   예약대기: ❌ 불가

👉 코레일 바로가기
```

---

## ⚠️ 주의사항
- GitHub Actions 무료 플랜: 월 **2,000분** 제공 (5분마다 실행 시 약 월 900분 사용)
- 취소표 발견 시에만 텔레그램 알림 전송 (미발견 시 무음)
- 코레일 서버 점검 시간(보통 새벽 1~5시)에는 오류가 날 수 있으나 무시해도 됩니다
- 자동 예매 기능은 없으며, 알림 수신 후 **직접 예매**해야 합니다
