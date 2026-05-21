"""
KTX 취소표 알림 봇 v3
코레일 웹사이트 로그인 후 취소표를 조회하고 텔레그램으로 알림을 전송합니다.
"""

import os
import re
import requests
from datetime import datetime

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://www.letskorail.com/",
    "Origin": "https://www.letskorail.com",
    "X-Requested-With": "XMLHttpRequest",
}

session = requests.Session()
session.headers.update(HEADERS)


def now():
    return datetime.now().strftime("%H:%M:%S")


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=10)
    return r.ok


def login():
    # 1) 메인 페이지 접속 (쿠키 획득)
    session.get("https://www.letskorail.com/", timeout=15)

    # 2) 로그인
    url = "https://www.letskorail.com/korail/com/login/loginAjax.do"
    payload = {
        "strMemberNo": KORAIL_ID,
        "strPwd": KORAIL_PW,
        "Device": "W",
        "Version": "20231001",
    }
    try:
        r = session.post(url, data=payload, timeout=15)
        print(f"[{now()}] 로그인 상태코드: {r.status_code}")
        print(f"[{now()}] 로그인 응답: {r.text[:300]}")
        
        if r.status_code == 200:
            try:
                data = r.json()
                if data.get("strResult") == "SUCC" or "SUCC" in r.text:
                    print(f"[{now()}] ✅ 로그인 성공")
                    return True
            except:
                if "SUCC" in r.text or r.status_code == 200:
                    print(f"[{now()}] ✅ 로그인 성공 (쿠키 방식)")
                    return True
        print(f"[{now()}] ❌ 로그인 실패")
        return False
    except Exception as e:
        print(f"[{now()}] ❌ 로그인 예외: {e}")
        return False


def search_trains():
    dep_code = STATION_CODE.get(DEPARTURE, "0045")
    arr_code = STATION_CODE.get(ARRIVAL, "0001")
    
    url = "https://www.letskorail.com/ebizprd/EbizPrdTicketpr21100W_i1.do"
    payload = {
        "selGoDate": DATE,
        "selGoHour": DEP_TIME[:2],
        "selGoTrain": "100",  # KTX
        "txtGoStart": dep_code,
        "txtGoEnd": arr_code,
        "txtPsgFlg_1": "1",
        "txtPsgFlg_2": "0",
        "txtPsgFlg_3": "0",
        "txtPsgFlg_4": "0",
        "txtPsgFlg_5": "0",
        "txtSeatAttCd_2": "000",
        "txtSeatAttCd_3": "000",
        "txtSeatAttCd_4": "015",
    }
    try:
        r = session.post(url, data=payload, timeout=15)
        print(f"[{now()}] 열차조회 상태코드: {r.status_code}")
        print(f"[{now()}] 열차조회 응답 일부: {r.text[:500]}")
        
        try:
            data = r.json()
            return data.get("trnsRVList", [])
        except:
            # HTML 응답인 경우 파싱 시도
            print(f"[{now()}] JSON 파싱 실패, HTML 응답으로 처리")
            return parse_html_trains(r.text)
    except Exception as e:
        print(f"[{now()}] ❌ 열차조회 예외: {e}")
        return []


def parse_html_trains(html):
    """HTML에서 열차 정보 파싱 (폴백)"""
    trains = []
    # KTX 열차번호 패턴 찾기
    pattern = r'KTX.*?(\d{3,4}).*?(\d{2}:\d{2}).*?(\d{2}:\d{2})'
    matches = re.findall(pattern, html)
    for m in matches[:10]:
        trains.append({
            "열차번호": m[0],
            "출발시각": m[1].replace(":", ""),
            "도착시각": m[2].replace(":", ""),
            "gnrmFlg": "Y",
            "stndFlg": "N",
            "rsvWaitFlg": "N",
        })
    return trains


def find_available(trains):
    available = []
    for t in trains:
        special_sold = t.get("stndFlg") == "N"
        general_sold = t.get("gnrmFlg") == "N"
        has_seat = not special_sold or not general_sold
        rsv_wait = t.get("rsvWaitFlg", "N")
        if has_seat or rsv_wait == "Y":
            dep = t.get("dptTm", t.get("출발시각", ""))
            arr = t.get("arvTm", t.get("도착시각", ""))
            dep_fmt = f"{dep[:2]}:{dep[2:4]}" if len(dep) >= 4 else dep
            arr_fmt = f"{arr[:2]}:{arr[2:4]}" if len(arr) >= 4 else arr
            available.append({
                "열차번호": t.get("trnNo", t.get("열차번호", "")),
                "출발시각": dep_fmt,
                "도착시각": arr_fmt,
                "일반실":   "✅ 예매가능" if not general_sold else "❌ 매진",
                "특실":     "✅ 예매가능" if not special_sold else "❌ 매진",
                "예약대기": "✅ 가능"     if rsv_wait == "Y"  else "❌ 불가",
            })
    return available


def format_message(trains):
    header = (
        f"🚄 <b>KTX 취소표 알림</b>\n"
        f"📍 {DEPARTURE} → {ARRIVAL}\n"
        f"📅 {DATE[:4]}-{DATE[4:6]}-{DATE[6:]}\n"
        f"🕐 확인: {now()}\n"
        f"{'─'*28}\n\n"
    )
    body = ""
    for t in trains:
        body += (
            f"🚅 <b>KTX {t['열차번호']}호</b>  {t['출발시각']} → {t['도착시각']}\n"
            f"   일반실: {t['일반실']}\n"
            f"   특  실: {t['특실']}\n"
            f"   예약대기: {t['예약대기']}\n\n"
        )
    return header + body + "👉 <a href='https://www.letskorail.com'>코레일 바로가기</a>"


def main():
    print(f"[{now()}] KTX 취소표 확인 시작 | {DEPARTURE}→{ARRIVAL} | {DATE}")

    if not login():
        send_telegram("⚠️ 코레일 로그인 실패. 아이디/비밀번호를 확인하세요.")
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
        print(f"[{now()}] 예매 가능한 열차 없음")


if __name__ == "__main__":
    main()
