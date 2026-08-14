import requests
from datetime import datetime, timedelta
from urllib.parse import unquote


# =========================================================
# 기상청 단기예보 API
# =========================================================

FORECAST_API_URL = (
    "https://apis.data.go.kr/1360000/"
    "VilageFcstInfoService_2.0/getVilageFcst"
)


# =========================================================
# 기상청 초단기실황 API
# 현재 관측 기온 / 습도 / 풍속
# =========================================================

CURRENT_API_URL = (
    "https://apis.data.go.kr/1360000/"
    "VilageFcstInfoService_2.0/getUltraSrtNcst"
)


# =========================================================
# 주요 지역 격자 좌표
# =========================================================

LOCATION_GRID = {
    "서울": (60, 127),
    "인천": (55, 124),
    "부산": (98, 76),
    "대구": (89, 90),
    "광주": (58, 74),
    "대전": (67, 100),
    "울산": (102, 84),
    "세종": (66, 103),
}


# =========================================================
# 인증키 정리
# =========================================================

def clean_service_key(service_key):

    """
    공공데이터포털 인증키가
    한 번 또는 여러 번 URL 인코딩되어 있어도
    정상적인 형태로 되돌린다.
    """

    while "%" in service_key:

        decoded_key = unquote(service_key)

        if decoded_key == service_key:
            break

        service_key = decoded_key

    return service_key


# =========================================================
# 단기예보 최신 발표시간
# =========================================================

def get_latest_base_time():

    now = datetime.now()

    base_hours = [
        2, 5, 8, 11,
        14, 17, 20, 23
    ]

    available_hours = [
        hour
        for hour in base_hours
        if hour <= now.hour
    ]

    if not available_hours:

        base_date = now - timedelta(days=1)
        base_hour = 23

    else:

        base_date = now
        base_hour = max(available_hours)

    base_date_str = base_date.strftime("%Y%m%d")
    base_time_str = f"{base_hour:02d}00"

    return base_date_str, base_time_str


# =========================================================
# 단기예보 가져오기
# =========================================================

def get_weather(service_key, nx, ny):

    service_key = clean_service_key(service_key)

    base_date, base_time = get_latest_base_time()

    params = {

        "serviceKey": service_key,

        "pageNo": 1,

        "numOfRows": 1000,

        "dataType": "JSON",

        "base_date": base_date,

        "base_time": base_time,

        "nx": nx,

        "ny": ny,
    }

    response = requests.get(
        FORECAST_API_URL,
        params=params,
        timeout=30
    )

    if response.status_code != 200:

        print("================================")
        print("기상청 단기예보 API 오류")
        print("HTTP 상태:", response.status_code)
        print("응답:", response.text)
        print("================================")

        response.raise_for_status()

    data = response.json()

    return data


# =========================================================
# 단기예보 데이터 정리
# =========================================================

def parse_weather_data(data):

    items = (
        data["response"]
        ["body"]
        ["items"]
        ["item"]
    )

    weather = {}

    for item in items:

        category = item["category"]

        date = item["fcstDate"]

        time = item["fcstTime"]

        key = f"{date}_{time}"

        if key not in weather:

            weather[key] = {

                "date": date,

                "time": time,
            }

        if category == "TMP":

            weather[key]["temperature"] = item["fcstValue"]

        elif category == "REH":

            weather[key]["humidity"] = item["fcstValue"]

        elif category == "POP":

            weather[key]["rain_probability"] = item["fcstValue"]

        elif category == "PCP":

            weather[key]["rain_amount"] = item["fcstValue"]

        elif category == "SKY":

            weather[key]["sky"] = item["fcstValue"]

        elif category == "WSD":

            weather[key]["wind_speed"] = item["fcstValue"]

    return list(weather.values())


# =========================================================
# 폭염 위험도 계산
# =========================================================

def calculate_heat_risk(
    temperature,
    humidity,
    wind_speed=0
):

    try:

        temperature = float(temperature)

        humidity = float(humidity)

        wind_speed = float(wind_speed)

    except (ValueError, TypeError):

        return 0


    score = 0


    # -----------------------------------------
    # 기온
    # -----------------------------------------

    if temperature >= 35:

        score += 60

    elif temperature >= 33:

        score += 50

    elif temperature >= 31:

        score += 40

    elif temperature >= 29:

        score += 25

    elif temperature >= 27:

        score += 10


    # -----------------------------------------
    # 습도
    # -----------------------------------------

    if humidity >= 80:

        score += 25

    elif humidity >= 70:

        score += 20

    elif humidity >= 60:

        score += 15

    elif humidity >= 50:

        score += 8


    # -----------------------------------------
    # 풍속
    # -----------------------------------------

    if wind_speed < 1:

        score += 10

    elif wind_speed < 2:

        score += 5


    return min(score, 100)


# =========================================================
# 위험도 단계
# =========================================================

def get_risk_level(score):

    if score >= 80:

        return "매우 높음"

    elif score >= 60:

        return "높음"

    elif score >= 40:

        return "주의"

    else:

        return "낮음"


# =========================================================
# 시간별 날씨에 위험도 추가
# =========================================================

def add_heat_risk(weather_list):

    for weather in weather_list:

        temperature = weather.get(
            "temperature",
            0
        )

        humidity = weather.get(
            "humidity",
            0
        )

        wind_speed = weather.get(
            "wind_speed",
            0
        )

        score = calculate_heat_risk(

            temperature,

            humidity,

            wind_speed
        )

        weather["risk_score"] = score

        weather["risk_level"] = (
            get_risk_level(score)
        )

    return weather_list


# =========================================================
# ⭐ 현재 관측 날씨
# 초단기실황 API
# =========================================================

def get_current_weather(
    service_key,
    nx,
    ny
):

    service_key = clean_service_key(
        service_key
    )

    now = datetime.now()


    # -----------------------------------------
    # 초단기실황은 매시 정각 자료
    # 발표 직후에는 이전 시간 자료 사용
    # -----------------------------------------

    if now.minute < 10:

        observation_time = now - timedelta(
            hours=1
        )

    else:

        observation_time = now


    base_date = observation_time.strftime(
        "%Y%m%d"
    )

    base_time = observation_time.strftime(
        "%H00"
    )


    params = {

        "serviceKey": service_key,

        "pageNo": 1,

        "numOfRows": 1000,

        "dataType": "JSON",

        "base_date": base_date,

        "base_time": base_time,

        "nx": nx,

        "ny": ny
    }


    response = requests.get(

        CURRENT_API_URL,

        params=params,

        timeout=10
    )


    if response.status_code != 200:

        print("================================")
        print("기상청 초단기실황 API 오류")
        print("HTTP 상태:", response.status_code)
        print("응답:", response.text)
        print("================================")

        response.raise_for_status()


    data = response.json()


    # -----------------------------------------
    # API 응답 확인
    # -----------------------------------------

    if data["response"]["header"]["resultCode"] != "00":

        raise Exception(
            "기상청 현재 날씨 API 오류: "
            + data["response"]["header"]["resultMsg"]
        )


    items = (

        data["response"]

        ["body"]

        ["items"]

        ["item"]
    )


    current = {}


    for item in items:

        category = item["category"]

        value = item["obsrValue"]

        current[category] = value


    return current
