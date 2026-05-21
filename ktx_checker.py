"""
KTX 취소표 알림 봇 v4
korail2 라이브러리를 사용해 안정적으로 조회합니다.
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
ARR_TIME  = os.environ.get("ARR_TIME",  "090000")  # 이 시각 이전 출발 열차만


def now():
    return datetime.now().strftime("%H:%M:%S")


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=10)
    print(f"[{now()}] 텔레그램 전송: {'성공' if r.ok else '실패 ' + r.text}")
    return r.ok


def main():
    print(f"[{now()}] KTX 취소표 확인 시작 | {DEPARTURE}→{ARRIVAL} | {DATE} | {DEP_TIME[:2]}시~{ARR_TIME[:2]}시")

    try:
        from korail2 import Korail, TrainType, ReserveOption
    except ImportError:
        print("korail2 설치 필요")
        return

    try:
        korail = Korail(KORAIL_ID, KORAIL_PW, auto_login=True)
        print(f"[{now()}] ✅ 로그인 성공")
    except Exception as e:
        print(f"[{now()}] ❌ 로그인 실패: {e}")
        send_telegram(f"⚠️ 코레일 로그인 실패: {e}\n아이디/비밀번호를 확인하세요.")
        return

    try:
        trains = korail.search_train(
            dep=DEPARTURE,
            arr=ARRIVAL,
            date=DATE,
            time=DEP_TIME,
            train_type=TrainType.KTX,
        )
        print(f"[{now()}] 조회된 열차 수: {len(trains)}")
    except Exception as e:
        print(f"[{now()}] ❌ 열차 조회 실패: {e}")
        return

    # 출발 시각 필터 (DEP_TIME ~ ARR_TIME 사이만)
    dep_min = int(DEP_TIME[:4])
    arr_max = int(ARR_TIME[:4])

    available = []
    for t in trains:
        dep_hhmm = int(t.dep_time[:4]) if hasattr(t, 'dep_time') and t.dep_time else 9999
        if not (dep_min <= dep_hhmm <= arr_max):
            continue

        general_ok  = getattr(t, 'general_seat_state', '') != '매진'
        special_ok  = getattr(t, 'special_seat_state', '') != '매진'
        wait_ok     = getattr(t, 'reserve_wait_possible_name', '') == '예약대기 가능'

        if general_ok or special_ok or wait_ok:
            dep = t.dep_time if hasattr(t, 'dep_time') else ""
            arr = t.arr_time if hasattr(t, 'arr_time') else ""
            dep_fmt = f"{dep[:2]}:{dep[2:4]}" if len(dep) >= 4 else dep
            arr_fmt = f"{arr[:2]}:{arr[2:4]}" if len(arr) >= 4 else arr
            available.append({
                "열차번호": getattr(t, 'train_no', ''),
                "출발시각": dep_fmt,
                "도착시각": arr_fmt,
                "일반실":   "✅ 예매가능" if general_ok else "❌ 매진",
                "특실":     "✅ 예매가능" if special_ok else "❌ 매진",
                "예약대기": "✅ 가능"     if wait_ok    else "❌ 불가",
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
        msg = header + body + "👉 <a href='https://www.letskorail.com'>코레일 바로가기</a>"
        send_telegram(msg)
    else:
        print(f"[{now()}] 예매 가능한 열차 없음 — 알림 미전송")


if __name__ == "__main__":
    main()
