import streamlit as st
import datetime
from openai import OpenAI
import textwrap

client = OpenAI(
    api_key=st.secrets["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1"
)

def generate_schedule_comment(
    schedule,
    current_risk,
    recommended_time,
    recommended_risk,
    health_conditions,
    moved=False
):

    health_text = ", ".join(health_conditions)

    if moved:
        action_text = f"""
현재 일정은 폭염 위험도가 상대적으로 높아
{recommended_time}으로 일정을 조정하는 것이 좋습니다.
"""
    else:
        action_text = """
현재 일정은 실내 활동이거나 일정 변경이 필요하지 않은 조건이므로
기존 시간대로 진행하는 것을 권장합니다.
"""

    prompt = f"""
당신은 폭염 상황에서 사용자의 하루 일정을
안전하게 계획할 수 있도록 돕는 일정 안내 서비스입니다.

다음 정보를 바탕으로 실제 일정 관리 서비스에서
사용자에게 보여줄 자연스러운 안내문을 작성하세요.

[일정]
{schedule["name"]}

[장소]
{schedule["place"]}

[활동 강도]
{schedule["level"]}

[현재 일정]
{schedule["start"].strftime("%H:%M")} ~ {schedule["end"].strftime("%H:%M")}

[현재 폭염 위험도]
{current_risk}점

[추천 시간]
{recommended_time}

[추천 시간의 폭염 위험도]
{recommended_risk}점

[사용자의 건강 관련 주의사항]
{health_text if health_text else "선택하지 않음"}

[일정 조정 판단]
{action_text}

작성 규칙:
- 3~4문장으로 작성하세요.
- 현재 일정의 폭염 위험도를 설명하세요.
- 일정이 변경되는 경우에는 왜 변경하는 것이 좋은지 설명하세요.
- 일정이 변경되지 않는 경우에는 기존 일정을 유지해도 되는 이유를 설명하세요.
- 실내 활동은 야외 활동보다 폭염의 직접적인 영향을 덜 받는다는 점을 고려하세요.
- 낮은 강도의 실내 활동은 특별한 이유가 없다면 시간을 변경하도록 권유하지 마세요.
- 사용자의 건강 관련 주의사항이 입력된 경우 이를 고려한 일반적인 생활 안내를 포함하세요.
- 의학적 진단이나 치료 방법은 제시하지 마세요.
- 불필요하게 불안감을 조성하지 마세요.
- 'AI', '인공지능', 'LLM'이라는 표현을 사용하지 마세요.
- 오전 8시 이전의 시간을 새로운 추천 시간으로 제시하지 마세요.
- 실제 서비스에서 보여주는 안내문처럼 자연스럽게 작성하세요.
"""

    try:

        response = client.chat.completions.create(
            model="solar-pro4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "사용자의 날씨 기반 일정 계획을 "
                        "도와주는 서비스입니다."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

    except Exception:

        if moved:
            return (
                f"현재 일정의 폭염 위험도는 {current_risk}점입니다. "
                f"{recommended_time}으로 조정하면 위험도를 "
                f"{recommended_risk}점까지 낮출 수 있습니다. "
                f"더운 시간대에는 무리한 야외활동을 피하고 충분한 휴식을 취하는 것을 권장합니다."
            )

        return (
            f"현재 일정의 폭염 위험도는 {current_risk}점입니다. "
            f"현재 일정은 그대로 진행해도 괜찮은 조건입니다. "
            f"실내 활동이라면 실내 온도를 적절하게 유지하고 "
            f"무리하지 않는 범위에서 일정을 진행해 주세요."
        )

from weather import (
    get_weather,
    get_current_weather,
    parse_weather_data,
    add_heat_risk,
    LOCATION_GRID
)

# -----------------------------------------
# 페이지 기본 설정
# -----------------------------------------

st.set_page_config(
    page_title="ThermoPlan",
    page_icon="☀️",
    layout="wide"
)


# -----------------------------------------
# Apple 스타일 CSS
# -----------------------------------------

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background-color: #F5F5F7;
}

.block-container {
    max-width: 1100px;
    padding-top: 55px;
    padding-bottom: 60px;
}


/* 제목 */

h1 {
    font-size: 40px !important;
    font-weight: 700 !important;
    letter-spacing: -1.5px;
    color: #1D1D1F;
    margin-bottom: 8px;
}

h2 {
    font-size: 28px !important;
    font-weight: 600 !important;
    letter-spacing: -1px;
    color: #1D1D1F;
}

h3 {
    font-size: 20px !important;
    font-weight: 600 !important;
    color: #1D1D1F;
}

p {
    color: #6E6E73;
}


/* 카드 */

.card {
    background: #FFFFFF;
    padding: 24px;
    border-radius: 16px;
    border: 1px solid #E5E5EA;
    margin-bottom: 20px;
}


/* 날씨 온도 */

.weather-temp {
    font-size: 58px;
    font-weight: 700;
    letter-spacing: -3px;
    color: #1D1D1F;
}

.weather-sub {
    color: #6E6E73;
    font-size: 16px;
}


/* 위험도 */

.risk-high {
    color: #FF3B30;
    font-weight: 600;
    font-size: 18px;
}

.risk-warning {
    color: #FF9500;
    font-weight: 600;
    font-size: 18px;
}

.risk-low {
    color: #34C759;
    font-weight: 600;
    font-size: 18px;
}


/* 버튼 */

.stButton > button {
    width: 100%;
    min-height: 48px;

    border-radius: 12px;
    border: 1px solid #D2D2D7;

    background-color: #FFFFFF;
    color: #1D1D1F;

    font-size: 15px;
    font-weight: 600;

    transition: all 0.15s ease;
}

.stButton > button:hover {
    background-color: #F2F2F7;
    border-color: #B8B8BE;
    color: #1D1D1F;
}

.stButton > button:active {
    transform: scale(0.98);
}

.stButton > button:active {
    background-color: #E5E5EA;
    transform: scale(0.98);
}


/* 구분선 */

hr {
    border: none;
    border-top: 1px solid #D2D2D7;
    margin: 30px 0;
}

.recommend-card {
    background: #F7F7F7;
    border-radius: 18px;
    padding: 22px;
    margin-top: 16px;
    margin-bottom: 20px;
    border: 1px solid #E5E5E5;
}

/* -----------------------------------------
   최종 일정 카드
----------------------------------------- */

.schedule-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    width: 100%;
    margin-top: 16px;
    margin-bottom: 30px;
}

.schedule-card {
    background: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 18px;
    padding: 22px;
    min-height: 190px;
    box-sizing: border-box;
    transition: all 0.2s ease;
}

.schedule-card:hover {
    transform: translateY(-2px);
    border-color: #D2D2D7;
    box-shadow: 0 8px 24px rgba(0,0,0,0.05);
}

.schedule-time {
    font-size: 15px;
    color: #86868B;
    margin-bottom: 16px;
    font-weight: 500;
}

.schedule-name {
    font-size: 22px;
    font-weight: 600;
    color: #1D1D1F;
    margin-bottom: 10px;
}

.schedule-info {
    font-size: 14px;
    color: #6E6E73;
    margin-bottom: 20px;
}

.schedule-risk {
    font-size: 14px;
    margin-bottom: 16px;
}

.schedule-moved {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 8px;
    background: #F2F2F7;
    color: #6E6E73;
    font-size: 12px;
}

.schedule-normal {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 8px;
    background: #F2F2F7;
    color: #6E6E73;
    font-size: 12px;
}


/* -----------------------------------------
   언어모델 일정 안내
----------------------------------------- */

.guide-card {
    background: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 16px;
}

.guide-title {
    font-size: 20px;
    font-weight: 600;
    color: #1D1D1F;
    margin-bottom: 12px;
}

.guide-text {
    font-size: 15px;
    line-height: 1.75;
    color: #6E6E73;
}


/* 모바일 */

@media (max-width: 800px) {

    .schedule-grid {
        grid-template-columns: 1fr;
    }

}


.recommend-card h3 {
    margin-top: 4px;
    margin-bottom: 10px;
    font-size: 24px;
    font-weight: 600;
    color: #1D1D1F;
}

.recommend-card p {
    color: #6E6E73;
    line-height: 1.6;
}

/* 삭제 버튼 */

div[data-testid="stButton"] button[kind="secondary"] {
    min-height: 40px;
    font-size: 14px;
    color: #6E6E73;
}

/* 최종 일정 카드 */

.final-schedule-card {
    background: #FFFFFF;

    border: 1px solid #E5E5EA;

    border-radius: 18px;

    padding: 22px;

    min-height: 190px;

    margin-bottom: 18px;

    transition:
        transform 0.15s ease,
        box-shadow 0.15s ease;
}

.final-schedule-card:hover {

    transform: translateY(-2px);

    box-shadow:
        0 6px 20px rgba(0, 0, 0, 0.06);
}


/* 일정 시간 */

.schedule-time {

    color: #6E6E73;

    font-size: 14px;

    font-weight: 500;

    margin-bottom: 12px;
}


/* 일정 이름 */

.schedule-name {

    color: #1D1D1F;

    font-size: 22px;

    font-weight: 600;

    letter-spacing: -0.5px;

    margin-bottom: 8px;
}


/* 일정 정보 */

.schedule-info {

    color: #6E6E73;

    font-size: 14px;

    margin-bottom: 20px;
}


/* 일정 변경 */

.schedule-change {

    margin-top: 14px;

    padding-top: 12px;

    border-top: 1px solid #E5E5EA;

    color: #6E6E73;

    font-size: 13px;
}


/* 일정 유지 */

.schedule-normal {

    margin-top: 14px;

    padding-top: 12px;

    border-top: 1px solid #E5E5EA;

    color: #86868B;

    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)   

st.markdown("""
<style>

.risk-high {
    color: #C9342E;
    font-weight: 600;
}

.risk-warning {
    color: #B76E00;
    font-weight: 600;
}

.risk-caution {
    color: #6B6B6B;
    font-weight: 600;
}

.risk-safe {
    color: #2F6F44;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)


# -----------------------------------------
# 헤더
# -----------------------------------------

st.markdown("# ThermoPlan")

st.markdown(
    "### 날씨와 건강을 고려한 스마트 일정 관리"
)

st.write(
    "오늘의 날씨를 바탕으로 일정에 적합한 시간을 찾아드립니다."
)

st.divider()

# -----------------------------------------
# 지역 선택
# -----------------------------------------

st.markdown("## 위치")

st.markdown(
    "일정을 분석할 지역을 선택해주세요."
)

location = st.selectbox(
    "지역",
    [
        "서울",
        "인천",
        "부산",
        "대구",
        "광주",
        "대전",
        "울산",
        "세종"
    ],
    key="weather_location"
)



# -----------------------------------------
# 선택한 지역의 격자 좌표
# -----------------------------------------

nx, ny = LOCATION_GRID[location]

# -----------------------------------------
# API 키
# -----------------------------------------

service_key = st.secrets["KMA_API_KEY"]



# -----------------------------------------
# 현재 실시간 날씨
# -----------------------------------------

try:

    current_weather = get_current_weather(
        service_key,
        nx,
        ny
    )

    current_temperature = float(
        current_weather.get("T1H", 0)
    )

    current_humidity = float(
        current_weather.get("REH", 0)
    )

    current_wind = float(
        current_weather.get("WSD", 0)
    )


    # -----------------------------------------
    # 현재 날씨를 바탕으로 간단한 상태 표시
    # -----------------------------------------

    if current_temperature >= 33:

        current_status = "폭염 주의"
        current_class = "risk-high"

    elif current_temperature >= 30:

        current_status = "더운 날씨"
        current_class = "risk-warning"

    elif current_temperature >= 25:

        current_status = "다소 더운 날씨"
        current_class = "risk-caution"

    else:

        current_status = "쾌적한 날씨"
        current_class = "risk-safe"


    # -----------------------------------------
    # 화면 표시
    # -----------------------------------------

    st.markdown(
        f"""
        <div class="card">

        <div class="weather-sub">
        현재 관측 기상정보
        </div>

        <div class="weather-temp">
        {current_temperature:.0f}°
        </div>

        <div class="weather-sub">
        습도 {current_humidity:.0f}% ·
        풍속 {current_wind:.1f}m/s
        </div>

        <br>

        <div class="{current_class}">
        ● {current_status}
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )

except Exception as e:

    st.error(
        "현재 기상정보를 불러오지 못했습니다."
    )

    st.caption(
        f"오류 내용: {e}"
    )



# -----------------------------------------
# 일정 데이터 초기화
# -----------------------------------------

if "schedules" not in st.session_state:
    st.session_state.schedules = []



# -----------------------------------------
# 기상청 날씨 불러오기
# -----------------------------------------

if st.button("날씨 정보 확인", use_container_width=True):

    try:

        with st.spinner("날씨 정보를 불러오는 중입니다."):

            weather_data = get_weather(
                service_key,
                nx,
                ny
            )

            weather_list = parse_weather_data(
                weather_data
            )

            weather_list = add_heat_risk(
                weather_list
            )

            st.session_state.weather = weather_list

        st.success("날씨 정보를 불러왔습니다.")

    except Exception as e:

        st.error(
            "날씨 정보를 가져오지 못했습니다."
        )

        st.write(e)

# -----------------------------------------
# 시간별 날씨 표시
# -----------------------------------------

if "weather" in st.session_state:

    st.markdown("## 시간별 날씨")

    weather_list = st.session_state.weather

    for weather in weather_list[:12]:

        time_text = weather["time"][:2] + ":" + weather["time"][2:]

        temperature = weather.get(
            "temperature",
            "-"
        )

        humidity = weather.get(
            "humidity",
            "-"
        )

        rain_probability = weather.get(
            "rain_probability",
            "-"
        )

        risk_score = weather.get(
            "risk_score",
            0
        )

        risk_level = weather.get(
            "risk_level",
            "낮음"
        )

        if risk_score >= 80:
            risk_class = "risk-high"

        elif risk_score >= 60:
            risk_class = "risk-warning"

        elif risk_score >= 40:
            risk_class = "risk-caution"

        else:
            risk_class = "risk-safe"

        st.markdown(
            f"""
            <div class="card">

            <div class="weather-sub">
            {time_text}
            </div>

            <div class="weather-temp"
                 style="font-size: 36px;">
            {temperature}°
            </div>

            <p>
            습도 {humidity}% · 강수확률 {rain_probability}%
            </p>

            <p class = "{risk_class}">
            폭염 위험도 {risk_score}점 · {risk_level}
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )        

# -----------------------------------------
# 건강 관련 정보
# -----------------------------------------

st.markdown("## 건강 관련 정보")

st.markdown(
    "일정의 기상환경 위험도를 분석하기 위해 건강 관련 주의사항을 선택해주세요."
)

st.markdown("""
<div class="card">
""", unsafe_allow_html=True)

health_conditions = st.multiselect(
    "건강 관련 주의사항",
    [
        "고혈압",
        "심혈관 관련 질환",
        "당뇨",
        "호흡기 관련 질환",
        "해당 없음"
    ],
    placeholder="해당하는 항목을 선택해주세요"
)
if "해당 없음" in health_conditions and len(health_conditions) > 1:
    st.warning("'해당 없음'을 선택한 경우 다른 항목은 선택할 수 없습니다.")


st.markdown("""
<p style="
    font-size: 13px;
    color: #86868B;
    margin-top: 12px;
    margin-bottom: 0;
">
이 정보는 의료적 진단이나 치료를 위한 것이 아니라
기상환경에 따른 일정 위험도를 분석하기 위한 참고 정보로만 사용됩니다.
</p>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------
# 오늘의 일정
# -----------------------------------------

st.markdown("## 오늘의 일정")

st.markdown(
    "오늘 해야 할 일정을 입력하고, 날씨에 따라 일정을 조정할 수 있습니다."
)


# -----------------------------------------
# 일정 입력 카드
# -----------------------------------------

st.markdown("""
<div class="card">
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:

    schedule_name = st.text_input(
        "일정 이름",
        placeholder="예: 공원 산책",
        key="schedule_name"
    )

with col2:

    activity_type = st.selectbox(
        "활동 장소",
        ["야외", "실내"],
        key="activity_type"
    )


col3, col4 = st.columns(2)

with col3:

    start_time = st.time_input(
        "시작 시간",
        value=datetime.time(9, 0),
        step=1800,
        key="start_time"
    )

with col4:

    end_time = st.time_input(
        "종료 시간",
        value=datetime.time(10, 0),
        step=1800,
        key="end_time"
    )


col5, col6 = st.columns(2)

with col5:

    activity_level = st.selectbox(
        "활동 강도",
        ["낮음", "보통", "높음"],
        key="activity_level"
    )

with col6:

    changeable = st.selectbox(
        "일정 변경 가능 여부",
        ["변경 가능", "변경 불가능"],
        key="changeable"
    )


st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------
# 일정 추가 버튼
# -----------------------------------------

if st.button("일정 추가", use_container_width=True):

    if schedule_name.strip() == "":
        st.warning("일정 이름을 입력해주세요.")

    elif end_time <= start_time:
        st.warning("종료 시간은 시작 시간보다 늦어야 합니다.")

    else:

        new_schedule = {
            "name": schedule_name,
            "place": activity_type,
            "start": start_time,
            "end": end_time,
            "level": activity_level,
            "changeable": changeable
        }

        st.session_state.schedules.append(new_schedule)

        st.success(f"'{schedule_name}' 일정이 추가되었습니다.")

        st.rerun()


# -----------------------------------------
# 등록된 일정 표시
# -----------------------------------------

if st.session_state.schedules:

    st.markdown("## 등록된 일정")

    for i, schedule in enumerate(st.session_state.schedules):

        st.markdown(f"""
        <div class="card">

        <div class="weather-sub">
        {schedule["start"].strftime("%H:%M")}
        —
        {schedule["end"].strftime("%H:%M")}
        </div>

        <h3>
        {schedule["name"]}
        </h3>

        <p>
        {schedule["place"]} · {schedule["level"]} 활동
        </p>

        <p>
        일정 변경: {schedule["changeable"]}
        </p>

        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "삭제",
            key=f"delete_{i}",
            type="secondary"
        ):

            st.session_state.schedules.pop(i)

            st.rerun()
# -----------------------------------------
# 일정 재배치 관련 함수
# -----------------------------------------

def time_to_minutes(t):
    return t.hour * 60 + t.minute


def minutes_to_time(minutes):
    return datetime.time(
        hour=minutes // 60,
        minute=minutes % 60
    )


def is_overlapping(start1, end1, start2, end2):

    return (
        start1 < end2
        and end1 > start2
    )


def health_adjusted_risk(
    risk_score,
    schedule,
    health_conditions
):

    """
    건강 관련 주의사항을 일정 분석에 반영하기 위한
    보수적인 위험도 보정값.

    의료적 진단값이 아니라 일정 재배치를 위한
    서비스 내부의 참고 점수이다.
    """

    score = risk_score

    # 실내 활동에는 폭염 위험도 보정을 크게 적용하지 않음
    if schedule["place"] == "실내":
        return min(score, 100)

    # 야외 활동인 경우 건강 관련 주의사항을 고려
    if health_conditions:

        if "고혈압" in health_conditions:
            score += 8

        if "심혈관 관련 질환" in health_conditions:
            score += 10

        if "당뇨" in health_conditions:
            score += 7

        if "호흡기 관련 질환" in health_conditions:
            score += 5

    # 활동 강도도 반영
    if schedule["level"] == "높음":
        score += 8

    elif schedule["level"] == "보통":
        score += 4

    return min(score, 100)


def get_schedule_weather(
    schedule,
    weather_list,
    health_conditions
):

    start_hour = schedule["start"].hour
    end_hour = schedule["end"].hour

    result = []

    for weather in weather_list:

        weather_hour = int(
            weather["time"][:2]
        )

        if start_hour <= weather_hour < end_hour:

            base_score = weather.get(
                "risk_score",
                0
            )

            adjusted_score = health_adjusted_risk(
                base_score,
                schedule,
                health_conditions
            )

            result.append({
                **weather,
                "adjusted_risk": adjusted_score
            })

    return result


def calculate_schedule_risk(
    schedule,
    weather_list,
    health_conditions
):

    schedule_weather = get_schedule_weather(
        schedule,
        weather_list,
        health_conditions
    )

    if not schedule_weather:
        return None

    scores = [
        weather["adjusted_risk"]
        for weather in schedule_weather
    ]

    return round(
        sum(scores) / len(scores)
    )


def find_best_time(
    schedule,
    weather_list,
    schedules,
    health_conditions,
    current_index,
    reserved_schedules=None
):

    """
    하루 일정 안에서 다른 일정과 겹치지 않는
    현실적인 시간대를 찾는다.

    - 09:00 이전 추천 금지
    - 21:00 이후 추천 금지
    - 30분 단위
    - 기존 일정 및 이미 이동한 일정과 겹치지 않음
    """

    if reserved_schedules is None:
        reserved_schedules = []

    duration = (
        time_to_minutes(schedule["end"])
        - time_to_minutes(schedule["start"])
    )

    DAY_START = 9 * 60
    DAY_END = 21 * 60

    candidates = []

    for start_minutes in range(
        DAY_START,
        DAY_END - duration + 1,
        30
    ):

        end_minutes = start_minutes + duration

        candidate_start = minutes_to_time(start_minutes)
        candidate_end = minutes_to_time(end_minutes)

        overlap = False

        # -----------------------------------------
        # 기존 일정과 겹치는지 확인
        # -----------------------------------------

        for index, other in enumerate(schedules):

            if index == current_index:
                continue

            if is_overlapping(
                candidate_start,
                candidate_end,
                other["start"],
                other["end"]
            ):
                overlap = True
                break

        if overlap:
            continue

        # -----------------------------------------
        # 이미 재배치된 일정과도 겹치는지 확인
        # -----------------------------------------

        for other in reserved_schedules:

            if is_overlapping(
                candidate_start,
                candidate_end,
                other["start"],
                other["end"]
            ):
                overlap = True
                break

        if overlap:
            continue

        candidate_schedule = {
            **schedule,
            "start": candidate_start,
            "end": candidate_end
        }

        risk = calculate_schedule_risk(
            candidate_schedule,
            weather_list,
            health_conditions
        )

        if risk is None:
            continue

        original_start = time_to_minutes(
            schedule["start"]
        )

        distance = abs(
            start_minutes - original_start
        )

        candidates.append(
            (
                risk,
                distance,
                candidate_start,
                candidate_end
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (x[0], x[1])
    )

    best = candidates[0]

    return {
        "start": best[2],
        "end": best[3],
        "risk": best[0]
    }

# -----------------------------------------
# 일정 분석 버튼
# -----------------------------------------

st.markdown("")

if st.session_state.schedules:

    if st.button(
        "전체 일정 분석하기",
        use_container_width=True
    ):

        st.session_state.analyze = True

        st.success(
            "일정 분석을 준비하고 있습니다."
        )

# -----------------------------------------
# 일정 분석 결과
# -----------------------------------------

if st.session_state.get("analyze", False):

    st.markdown("---")

    st.markdown("## 일정 분석 결과")

    st.caption(
        "등록된 일정의 시간대, 활동 장소, 활동 강도와 폭염 위험도를 함께 비교했습니다."
    )

    if "weather" not in st.session_state:

        st.warning(
            "먼저 날씨 정보를 확인해주세요."
        )

    else:

        weather_list = st.session_state.weather

        analyzed_schedules = []
        reserved_schedules = []

        # -----------------------------------------
        # 1. 각각의 일정 분석
        # -----------------------------------------

        for index, schedule in enumerate(
            st.session_state.schedules
        ):

            current_risk = calculate_schedule_risk(
                schedule,
                weather_list,
                health_conditions
            )

            # 날씨 데이터가 없는 경우
            if current_risk is None:

                analyzed_schedules.append({
                    "original": schedule,
                    "final": schedule,
                    "current_risk": None,
                    "recommended_risk": None,
                    "moved": False,
                    "reason": "해당 시간대의 날씨 데이터를 확인할 수 없습니다."
                })

                continue

            # -----------------------------------------
            # 실내 + 낮은 활동
            # → 기본적으로 일정 유지
            # -----------------------------------------

            if (
                schedule["place"] == "실내"
                and schedule["level"] == "낮음"
            ):

                analyzed_schedules.append({
                    "original": schedule,
                    "final": schedule,
                    "current_risk": current_risk,
                    "recommended_risk": current_risk,
                    "moved": False,
                    "reason": "실내의 낮은 강도 활동이므로 기존 일정으로 진행합니다."
                })

                continue

            # -----------------------------------------
            # 일정 변경 불가능
            # → 기존 일정 유지
            # -----------------------------------------

            if schedule["changeable"] == "변경 불가능":

                analyzed_schedules.append({
                    "original": schedule,
                    "final": schedule,
                    "current_risk": current_risk,
                    "recommended_risk": current_risk,
                    "moved": False,
                    "reason": "일정 변경이 불가능하므로 기존 일정으로 진행합니다."
                })

                continue

            # -----------------------------------------
            # 위험도가 낮으면 그대로 유지
            # -----------------------------------------

            if current_risk < 60:

                analyzed_schedules.append({
                    "original": schedule,
                    "final": schedule,
                    "current_risk": current_risk,
                    "recommended_risk": current_risk,
                    "moved": False,
                    "reason": "현재 일정의 폭염 위험도가 비교적 낮아 기존 일정으로 진행합니다."
                })

                continue

            # -----------------------------------------
            # 위험도가 높은 경우
            # → 새로운 시간 탐색
            # -----------------------------------------

            best_time = find_best_time(
                schedule,
                weather_list,
                st.session_state.schedules,
                health_conditions,
                index,
                reserved_schedules
            )

            # 추천 시간 없음
            if best_time is None:

                analyzed_schedules.append({
                    "original": schedule,
                    "final": schedule,
                    "current_risk": current_risk,
                    "recommended_risk": current_risk,
                    "moved": False,
                    "reason": "다른 일정과 겹치지 않는 적절한 시간대를 찾지 못해 기존 일정으로 유지합니다."
                })

                continue

            # -----------------------------------------
            # 위험도 개선이 충분한 경우만 이동
            # -----------------------------------------

            improvement = (
                current_risk
                - best_time["risk"]
            )

            if best_time["risk"]  < current_risk:

                new_schedule = {
                    **schedule,
                    "start": best_time["start"],
                    "end": best_time["end"]
                }

                reserved_schedules.append(new_schedule)

                analyzed_schedules.append({
                    "original": schedule,
                    "final": new_schedule,
                    "current_risk": current_risk,
                    "recommended_risk": best_time["risk"],
                    "moved": True,
                    "reason": "폭염 위험도가 낮아지는 시간대로 조정했습니다."
                })

            else:

                analyzed_schedules.append({
                    "original": schedule,
                    "final": schedule,
                    "current_risk": current_risk,
                    "recommended_risk": current_risk,
                    "moved": False,
                    "reason": "시간을 변경해도 위험도 개선 폭이 크지 않아 기존 일정을 유지합니다."
                })

        # -----------------------------------------
        # 최종 일정 정렬
        # -----------------------------------------

        analyzed_schedules.sort(
            key=lambda x: time_to_minutes(
                x["final"]["start"]
            )
        )

        # -----------------------------------------
        # 최종 일정 저장
        # -----------------------------------------

        st.session_state.final_schedules = (
            analyzed_schedules
        )

        # -----------------------------------------
        # 최종 일정표
        # -----------------------------------------

        st.markdown("## 최종 일정")

        st.caption(
            "폭염 위험도와 일정 변경 가능 여부를 고려해 하루 일정을 정리했습니다."
        )

        cols = st.columns(3)

        for i, item in enumerate(analyzed_schedules):

            schedule = item["final"]

            start_text = schedule["start"].strftime("%H:%M")
            end_text = schedule["end"].strftime("%H:%M")

            risk = item["recommended_risk"] or 0

            if risk >= 80:
                risk_class = "risk-high"
                risk_text = "매우 높음"
            elif risk >= 60:
                risk_class = "risk-warning"
                risk_text = "높음"
            elif risk >= 40:
                risk_class = "risk-caution"
                risk_text = "주의"
            else:
                risk_class = "risk-safe"
                risk_text = "낮음"

            if item["moved"]:
                status = "날씨에 맞춰 시간 조정"
                status_class = "schedule-moved"
            else:
                status = "기존 일정 유지"
                status_class = "schedule-normal"

            with cols[i % 3]:

                html = f"""
                <div class="schedule-card">
                    <div class="schedule-time">{start_text} — {end_text}</div>
                    <div class="schedule-name">{schedule["name"]}</div>
                    <div class="schedule-info">{schedule["place"]} · {schedule["level"]} 활동</div>
                    <div class="{risk_class} schedule-risk">● 폭염 위험도 {risk}점 · {risk_text}</div>
                    <div class="{status_class}">{status}</div>
                </div>
                """

                st.markdown(textwrap.dedent(html).strip(), unsafe_allow_html=True)


        # -----------------------------------------
        # 일정 안내
        # -----------------------------------------

        st.markdown("## 일정 안내")

        for item in analyzed_schedules:

            schedule = item["original"]

            current_risk = item["current_risk"]
            recommended_risk = item["recommended_risk"]

            if current_risk is None:
                continue

            if item["moved"]:

                final_schedule = item["final"]

                recommended_time = (
                    f"{final_schedule['start'].strftime('%H:%M')}"
                    f" ~ "
                    f"{final_schedule['end'].strftime('%H:%M')}"
                )

            else:

                recommended_time = (
                    f"{schedule['start'].strftime('%H:%M')}"
                    f" ~ "
                    f"{schedule['end'].strftime('%H:%M')}"
                )

            # -----------------------------------------
            # Upstage 언어모델 안내
            # -----------------------------------------

            comment = generate_schedule_comment(
                schedule=schedule,
                current_risk=current_risk,
                recommended_time=recommended_time,
                recommended_risk=recommended_risk,
                health_conditions=health_conditions,
                moved=item["moved"]
            )

            # -----------------------------------------
            # 안내 카드
            # -----------------------------------------

            html = f"""
            <div class="guide-card">
                <div class="guide-title">{schedule["name"]}</div>
                <div class="guide-text">{comment}</div>
            </div>
            """

            st.markdown(textwrap.dedent(html).strip(), unsafe_allow_html=True)