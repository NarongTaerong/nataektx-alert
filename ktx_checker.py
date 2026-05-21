"""
KTX 취소표 알림 봇 v2
코레일 웹사이트 API를 통해 취소표를 조회하고 텔레그램으로 알림을 전송합니다.
"""
 
import os
import json
import requests
from datetime import datetime
 
# ── 환경 변수 ──────────────────────────────────────────────
KORAIL_ID = os.environ["KORAIL_ID"]
KORAIL_PW = os.environ["KORAIL_PW"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
 
DEPARTURE = os.environ.get("DEPARTURE", "부산")
ARRIVAL   = os.environ.get("ARRIVAL",   "서울")
DATE      = os.environ.get("DATE",      "20260523")
DEP_TIME  = os.environ.get("DEP_TIME",  "000000")
 
STATION_CODE = {
    "서울": "0001", "용산": "0002", "영등포": "0003", "수원": "0005",
    "천안아산": "0010", "오송": "0015", "대전": "0020", "김천구미": "0025",
    "동대구": "0030", "경주": "0035", "울산": "0040", "부산": "0045",
    "광명": "0044", "공주": "0096", "익산": "0047", "정읍": "0048",
    "광주송정": "0049", "나주": "0050", "목포": "0051",
}
 
BASE_URL = "https://smart.letskorail.com/classes/com.korail.mobile"
 
HEADERS = {
    "User-Agent": "korail2/2.0 (iPhone; iOS 16.0; Scale/3.00)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "application/json",
}
 
session = requests.Session()
session.headers.update(HEADERS)
 
 
def now():
    return datetime.now().strftime("%H:%M:%S")
 
 
# ── 코레일 로그인 ──────────────────────────────────────────
def login():
    url = f"{BASE_URL}.common.login"
    payload = {
        "txtMemberNo": KORAIL_ID,
        "txtPwd":      KORAIL_PW,
        "Device":      "I",
        "Version":     "231001001",
        "key":         "korail1234567890",
    }
    try:
        r = session.post(url, data=payload, timeout=15)
        print(f"[{now()}] 로그인 응답 코드: {r.status_code}")
        print(f"[{now()}] 로그인 응답 내용: {r.text[:200]}")
        data = r.json()
        success = data.get("strResult") == "SUCC"
        if success:
            print(f"[{now()}] ✅ 로그인 성공")
        else:
            print(f"[{now()}] ❌ 로그인 실패: {data.get('strMsg', '알 수 없는 오류')}")
        return success
    except Exception as e:
        print(f"[{now()}] ❌ 로그인 예외: {e}")
        return False
 
 
# ── 열차 조회 ──────────────────────────────────────────────
def search_trains():
    url = f"{BASE_URL}.seatMovie.ScheduleMovie"
    dep_code = STATION_CODE.get(DEPARTURE, DEPARTURE)
    arr_code = STATION_CODE.get(ARRIVAL, ARRIVAL)
    payload = {
        "txtGoAbrdDt":    DATE,
        "txtGoHour":      DEP_TIME,
        "txtGoStart":     dep_code,
        "txtGoEnd":       arr_code,
        "txtPsgFlg_1":    "1",
        "txtPsgFlg_2":    "0",
        "txtPsgFlg_3":    "0",
        "txtPsgFlg_4":    "0",
        "txtPsgFlg_5":    "0",
        "txtSeatAttCd_2": "000",
        "txtSeatAttCd_3": "000",
        "txtSeatAttCd_4": "015",
        "txtTrnGpCd":     "100",
        "KR":             "Y",
        "Device":         "I",
        "Version":        "231001001",
        "key":            "korail1234567890",
    }
    try:
        r = session.post(url, data=payload, timeout=15)
        print(f"[{now()}] 열차조회 응답 코드: {r.status_code}")
        print(f"[{now()}] 열차조회 응답 내용: {r.text[:300]}")
        data = r.json()
        return data.get("trnsRVList", [])
    except Exception as e:
        print(f"[{now()}] ❌ 열차조회 예외: {e}")
        return []
 
 
# ── 취소표 필터링 ──────────────────────────────────────────
def find_available(trains):
    available = []
    for t in trains:
        special_sold = t.get("stndFlg") == "N"
        general_sold = t.get("gnrmFlg") == "N"
        has_seat = not special_sold or not general_sold
        rsv_wait = t.get("rsvWaitFlg", "N")
        if has_seat or rsv_wait == "Y":
            available.append({
                "열차번호": t.get("trnNo", ""),
                "출발시각": t.get("dptTm", ""),
                "도착시각": t.get("arvTm", ""),
                "일반실":   "✅ 예매가능" if not general_sold else "❌ 매진",
                "특실":     "✅ 예매가능" if not special_sold else "❌ 매진",
                "예약대기": "✅ 가능"     if rsv_wait == "Y"  else "❌ 불가",
            })
    return available
 
 
# ── 텔레그램 전송 ──────────────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }
    r = requests.post(url, json=payload, timeout=10)
    return r.ok
 
 
def format_message(trains):
    header = (
        f"🚄 <b>KTX 취소표 알림</b>\n"
        f"📍 {DEPARTURE} → {ARRIVAL}\n"
        f"📅 {DATE[:4]}-{DATE[4:6]}-{DATE[6:]}\n"
        f"🕐 확인 시각: {now()}\n"
        f"{'─' * 28}\n\n"
    )
    body = ""
    for t in trains:
        dep = t["출발시각"]
        arr = t["도착시각"]
        dep_fmt = f"{dep[:2]}:{dep[2:4]}" if len(dep) >= 4 else dep
        arr_fmt = f"{arr[:2]}:{arr[2:4]}" if len(arr) >= 4 else arr
        body += (
            f"🚅 <b>KTX {t['열차번호']}호</b>  {dep_fmt} → {arr_fmt}\n"
            f"   일반실: {t['일반실']}\n"
            f"   특  실: {t['특실']}\n"
            f"   예약대기: {t['예약대기']}\n\n"
        )
    footer = "👉 <a href='https://www.letskorail.com'>코레일 바로가기</a>"
    return header + body + footer
 
 
# ── 메인 ───────────────────────────────────────────────────
def main():
    print(f"[{now()}] KTX 취소표 확인 시작 | {DEPARTURE}→{ARRIVAL} | {DATE}")
 
    if not login():
        send_telegram("⚠️ 코레일 로그인에 실패했습니다. 아이디/비밀번호를 확인하세요.")
        return
 
    trains = search_trains()
    print(f"[{now()}] 조회된 열차 수: {len(trains)}")
 
    available = find_available(trains)
    print(f"[{now()}] 예매 가능 열차 수: {len(available)}")
 
    if available:
        msg = format_message(available)
        ok = send_telegram(msg)
        print(f"[{now()}] 텔레그램 전송: {'성공' if ok else '실패'}")
    else:
        print(f"[{now()}] 예매 가능한 열차 없음 — 알림 미전송")
 
 
if __name__ == "__main__":
    main()
