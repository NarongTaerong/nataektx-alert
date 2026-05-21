"""
KTX 취소표 알림 봇 v5
korail2 로그인 + 직접 API 호출 방식
"""

import os
import requests
from datetime import datetime

KORAIL_ID = os.environ["KORAIL_ID"]
KORAIL_PW = os.environ["KORAIL_PW"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

DEPARTURE = os.environ.get("DEPARTURE", "부산")
ARRIVAL   = os.environ.get("ARRIVAL",   "서울")
DATE      = os.environ.get("DATE",      "20260523")
DEP_TIME  = os.environ.get("DEP_TIME",  "060000")
ARR_TIME  = os.environ.get("ARR_TIME",  "090000")

STATION_CODE = {
    "서울": "0001", "용산": "0002", "영등포": "0003", "수원": "0005",
    "천안아산": "0010", "오송": "0015", "대전": "0020", "김천구미": "0025",
    "동대구": "0030", "경주": "0035", "울산": "0040", "부산": "0045",
    "광명": "0044", "공주": "0096", "익산": "0047", "정읍": "0048",
    "광주송정": "0049", "나주": "0050", "목포": "0051",
}


def now():
    return datetime.now().strftime("%H:%M:%S")


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=10)
    print(f"[{now()}] 텔레그램 전송: {'성공' if r.ok else '실패'}")
    return r.ok


def main():
    print(f"[{now()}] KTX 취소표 확인 시작 | {DEPARTURE}→{ARRIVAL} | {DATE} | {DEP_TIME[:2]}시~{ARR_TIME[:2]}시")

    # korail2로 로그인해서 세션 쿠키 획득
    try:
        from korail2 import Korail
        korail = Korail(KORAIL_ID, KORAIL_PW, auto_login=True)
        print(f"[{now()}] ✅ 로그인 성공")
        # korail2 내부 세션 가져오기
        sess = korail._session
    except Exception as e:
        print(f"[{now()}] ❌ 로그인 실패: {e}")
        send_telegram(f"⚠️ 코레일 로그인 실패: {e}")
        return

    # 로그인된 세션으로 직접 열차 조회 API 호출
    dep_code = STATION_CODE.get(DEPARTURE, "0045")
    arr_code = STATION_CODE.get(ARRIVAL, "0001")

    url = "https://smart.letskorail.com/classes/com.korail.mobile.seatMovie.ScheduleMovie"
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
        "Device":         "A",
        "Version":        "230901001",
    }

    try:
        r = sess.post(url, data=payload, timeout=15)
        print(f"[{now()}] 열차조회 상태코드: {r.status_code}")
        print(f"[{now()}] 응답 일부: {r.text[:300]}")
        data = r.json()
        trains = data.get("trnsRVList", [])
        print(f"[{now()}] 조회된 열차 수: {len(trains)}")
    except Exception as e:
        print(f"[{now()}] ❌ 열차 조회 실패: {e}")
        return

    # 시간 필터 + 취소표 확인
    dep_min = int(DEP_TIME[:4])
    arr_max = int(ARR_TIME[:4])
    available = []

    for t in trains:
        dep = t.get("dptTm", "")
        dep_hhmm = int(dep[:4]) if len(dep) >= 4 else 9999
        if not (dep_min <= dep_hhmm <= arr_max):
            continue

        general_sold = t.get("gnrmFlg") == "N"
        special_sold = t.get("stndFlg") == "N"
        rsv_wait     = t.get("rsvWaitFlg", "N") == "Y"

        if not general_sold or not special_sold or rsv_wait:
            arr = t.get("arvTm", "")
            dep_fmt = f"{dep[:2]}:{dep[2:4]}" if len(dep) >= 4 else dep
            arr_fmt = f"{arr[:2]}:{arr[2:4]}" if len(arr) >= 4 else arr
            available.append({
                "열차번호": t.get("trnNo", ""),
                "출발시각": dep_fmt,
                "도착시각": arr_fmt,
                "일반실":   "✅ 예매가능" if not general_sold else "❌ 매진",
                "특실":     "✅ 예매가능" if not special_sold else "❌ 매진",
                "예약대기": "✅ 가능"     if rsv_wait          else "❌ 불가",
            })

    print(f"[{now()}] 예매 가능 열차 수: {len(available)}")

    if available:
        header = (
            f"🚄 <b>KTX 취소표 알림</b>\n"
            f"📍 {DEPARTURE} → {ARRIVAL}\n"
            f"📅 {DATE[:4]}-{DATE[4:6]}-{DATE[6:]}\n"
            f"🕐 {DEP_TIME[:2]}시 ~ {ARR_TIME[:2]}시 출발\n"
            f"{'─'*28}\n\n"
        )
        body = ""
        for t in available:
            body += (
                f"🚅 <b>KTX {t['열차번호']}호</b>  {t['출발시각']} → {t['도착시각']}\n"
                f"   일반실: {t['일반실']}\n"
                f"   특  실: {t['특실']}\n"
                f"   예약대기: {t['예약대기']}\n\n"
            )
        send_telegram(header + body + "👉 <a href='https://www.letskorail.com'>코레일 바로가기</a>")
    else:
        print(f"[{now()}] 예매 가능한 열차 없음 — 알림 미전송")


if __name__ == "__main__":
    main()
