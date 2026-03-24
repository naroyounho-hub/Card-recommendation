import streamlit as st
from src.chain import get_structured_recommendation, get_chat_stream

st.set_page_config(page_title="카드 추천 AI", page_icon="💳", layout="wide")

# 다크 + 비비드 테마 CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        color: #e0e0e0;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%);
        border-right: 1px solid #333;
    }
    .main-title {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00d2ff, #7b2ff7, #ff6bcb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }
    .sub-title {
        text-align: center;
        color: #888;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .card-box {
        background: linear-gradient(145deg, #1e1e36, #2a2a4a);
        border: 1px solid #444;
        border-radius: 16px;
        padding: 1.8rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .card-box:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(123, 47, 247, 0.3);
    }
    .card-number {
        position: absolute; top: 0; left: 0;
        background: linear-gradient(135deg, #7b2ff7, #00d2ff);
        color: #fff; font-weight: 800; font-size: 1rem;
        padding: 0.4rem 1rem 0.4rem 0.8rem;
        border-radius: 16px 0 16px 0;
    }
    .card-name {
        font-size: 1.4rem; font-weight: 700; color: #ffffff;
        margin-top: 1.5rem; margin-bottom: 0.2rem;
    }
    .card-company { font-size: 0.9rem; color: #aaa; margin-bottom: 1rem; }
    .reason-label {
        font-size: 0.8rem; font-weight: 600; color: #7b2ff7;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.3rem;
    }
    .reason-text { font-size: 0.95rem; color: #d0d0d0; line-height: 1.6; margin-bottom: 1rem; }
    .saving-badge {
        display: inline-block;
        background: linear-gradient(135deg, #00d2ff22, #7b2ff722);
        border: 1px solid #7b2ff7; color: #00d2ff;
        font-weight: 700; font-size: 1rem;
        padding: 0.5rem 1rem; border-radius: 10px; margin-top: 0.3rem;
    }
    .card-link {
        display: inline-block; margin-top: 0.8rem;
        color: #ff6bcb; font-size: 0.85rem;
        text-decoration: none; font-weight: 600;
    }
    .card-link:hover { color: #ff9de0; }
    .section-title {
        font-size: 1.5rem; font-weight: 700;
        margin: 2rem 0 1rem 0; padding-bottom: 0.5rem;
        border-bottom: 2px solid #7b2ff7;
    }
    .section-title-credit { color: #00d2ff; }
    .section-title-check { color: #ff6bcb; }
    .card-type-badge {
        display: inline-block; font-size: 0.75rem; font-weight: 600;
        padding: 0.2rem 0.6rem; border-radius: 6px;
        margin-left: 0.5rem; vertical-align: middle;
    }
    .badge-credit { background: rgba(0,210,255,0.15); color: #00d2ff; border: 1px solid #00d2ff; }
    .badge-check { background: rgba(255,107,203,0.15); color: #ff6bcb; border: 1px solid #ff6bcb; }
    .benefit-item { padding: 0.4rem 0; color: #ccc; font-size: 0.9rem; border-bottom: 1px solid #333; }
    .benefit-item:last-child { border-bottom: none; }
    .benefit-bullet { color: #7b2ff7; margin-right: 0.5rem; }
    .stButton > button {
        background: linear-gradient(135deg, #7b2ff7, #00d2ff) !important;
        color: white !important; border: none !important;
        font-weight: 700 !important; font-size: 1.1rem !important;
        padding: 0.7rem 2rem !important; border-radius: 12px !important;
    }
    .stButton > button:hover { opacity: 0.85 !important; }
    .stTextArea textarea {
        background: #1a1a2e !important; color: #e0e0e0 !important;
        border: 1px solid #444 !important; border-radius: 10px !important;
    }
    .stTextInput input {
        background: #1a1a2e !important; color: #e0e0e0 !important;
        border: 1px solid #444 !important; border-radius: 10px !important;
    }
    .stSelectbox > div > div { background: #1a1a2e !important; color: #e0e0e0 !important; }
    .chat-divider {
        text-align: center; color: #7b2ff7; font-weight: 600;
        margin: 2rem 0 1rem 0; padding: 0.5rem;
        border-top: 1px solid #333; border-bottom: 1px solid #333;
    }
    .chat-bubble-user {
        background: linear-gradient(135deg, #7b2ff7, #5a1fd6);
        color: #fff; padding: 0.8rem 1.2rem; border-radius: 16px 16px 4px 16px;
        margin: 0.5rem 0; max-width: 80%; margin-left: auto; text-align: right;
    }
    .chat-bubble-ai {
        background: linear-gradient(145deg, #1e1e36, #2a2a4a);
        border: 1px solid #444;
        color: #d0d0d0; padding: 0.8rem 1.2rem; border-radius: 16px 16px 16px 4px;
        margin: 0.5rem 0; max-width: 80%;
    }
    /* 채팅 입력창 하단 고정 */
    .fixed-chat-form {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(180deg, transparent, #0f0f1a 15%, #0f0f1a 100%);
        padding: 1rem 2rem 1.5rem 2rem;
        z-index: 999;
    }
    /* 고정 채팅창 아래 여백 확보 */
    .chat-bottom-spacer {
        height: 100px;
    }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown('<div class="main-title">CARD RECOMMEND AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">소비 패턴을 입력하면 AI가 맞춤 카드를 추천해드립니다</div>', unsafe_allow_html=True)

# 세션 상태 초기화
if "recommendation" not in st.session_state:
    st.session_state["recommendation"] = None
if "persona" not in st.session_state:
    st.session_state["persona"] = ""
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

# 사이드바
with st.sidebar:
    st.markdown("### 사용자 정보 입력")

    examples = {
        "직접 입력": "",
        "🎓 이세봉(26세, 유학생)": "서울 소재 대학원(공학계열) 재학 중인 중국 유학생입니다. 중국 부모님 송금 100만원+소액 과외 20만원으로 월 수입 약 120만원입니다. 고시원/원룸 월세 45만원, 학교 근처 중국음식점+편의점 식비 월 25만원, 지하철/버스 교통비 월 2만5천원, 중국 부모님 계좌 해외송금 수수료 월 1~2회 약 5만원, 알리익스프레스·타오바오 직구 해외결제 월 15만원, 외국인 전용 통신 요금제 월 3만원, OTT(아이치이·유튜브)+게임 여가비 월 2만원을 씁니다. 해외결제 수수료 면제, 해외송금 우대, 편의점 할인, 교통 할인이 필요합니다.",
        "✈️ 김지연(34세, 직장인 여성)": "서울 거주 마케팅회사 대리, 월 실수령 약 280만원입니다. 해외여행 연 2회(항공+숙박) 연 300만원, 피부과/내과 등 의료비 월 20만원, 주유·주차·정비 등 차량 유지비 연 180만원, 무신사·올리브영 등 온라인쇼핑 월 25만원, 스타벅스 출퇴근 커피 월 10만원을 씁니다. 항공 마일리지, 해외결제 수수료 면제, 의료비 할인이 필요합니다.",
        "🍗 박민수(42세, 자영업자)": "경기도 거주, 치킨 프랜차이즈 운영, 월 카드 지출 약 500만원(사업비 포함)입니다. 마트 식자재 대량 구매 월 200만원, 배달용 오토바이+자차 주유비 월 40만원, 사업장 회선 포함 통신/인터넷 월 20만원, 직원 식사 등 외식/회식 월 30만원, 배민 광고비 월 50만원을 씁니다. 높은 전월실적 조건 충족 가능하며, 마트 적립, 주유 할인, 포인트 환급 극대화가 필요합니다.",
        "💻 최수아(28세, 사회초년생)": "서울 자취, IT 스타트업 신입 개발자, 월 실수령 약 280만원입니다. 월세 자동이체 월 70만원, 배달앱(배민/쿠팡이츠) 위주 식비 월 35만원, 넷플릭스·유튜브프리미엄·Spotify 등 OTT/구독 월 4만원, 헬스장+PT 월 25만원, 쿠팡 로켓배송 쇼핑 월 25만원을 씁니다. 배달앱 할인, 구독서비스 할인, 쿠팡 적립, 스트리밍 혜택이 필요합니다.",
        "🏌️ 정태양(52세, 중년 직장인)": "수도권 거주 대기업 부장, 월 실수령 약 600만원입니다. 골프 라운딩+연습장 월 80만원, 접대 포함 고급 레스토랑 외식 월 70만원, 국내 리조트/호텔 여행 연 240만원, 백화점 의류/선물 월 50만원, 자녀 학원비 송금 월 100만원을 씁니다. 골프장 할인, 라운지 이용, 호텔 할인, 백화점 VIP 혜택, 높은 캐시백이 필요합니다.",
    }

    selected = st.selectbox("예시 페르소나 선택", list(examples.keys()))
    persona_text = st.text_area(
        "소비 패턴을 자유롭게 작성해주세요",
        value=examples[selected],
        height=200,
        placeholder="예: 대중교통으로 출퇴근하고, 편의점과 카페를 자주 이용하는 직장인입니다...",
    )

    st.divider()
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state["recommendation"] = None
        st.session_state["persona"] = ""
        st.session_state["chat_messages"] = []
        st.rerun()


# ──────────────────────────────────────
# 카드 렌더링 함수
# ──────────────────────────────────────
def render_cards(cards, section_title, section_class):
    if not cards:
        return
    st.markdown(f'<div class="section-title {section_class}">{section_title}</div>', unsafe_allow_html=True)
    for i, rec in enumerate(cards, 1):
        card_name = rec.get("card_name", "알 수 없음")
        card_company = rec.get("card_company", "")
        card_type = rec.get("card_type", "신용")
        reason = rec.get("reason", "")
        saving = rec.get("monthly_saving", "")
        card_url = rec.get("card_url", "")
        benefits = rec.get("benefits_summary", [])
        badge_class = "badge-credit" if card_type == "신용" else "badge-check"
        benefits_html = ""
        if benefits:
            items = "".join(f'<div class="benefit-item"><span class="benefit-bullet">▸</span>{b}</div>' for b in benefits)
            benefits_html = f'<div class="reason-label" style="margin-top:1rem;">주요 혜택</div>{items}'
        link_html = ""
        if card_url:
            link_html = f'<a class="card-link" href="{card_url}" target="_blank">카드 상세 페이지 바로가기 &rarr;</a>'
        st.markdown(f"""
        <div class="card-box">
            <div class="card-number">#{i}</div>
            <div class="card-name">{card_name}
                <span class="card-type-badge {badge_class}">{card_type}</span>
            </div>
            <div class="card-company">{card_company}</div>
            <div class="reason-label">추천 이유</div>
            <div class="reason-text">{reason}</div>
            <div class="reason-label">예상 월 절약 금액</div>
            <div class="saving-badge">{saving if saving else "산정 불가"}</div>
            {benefits_html}
            <br>{link_html}
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────
# 1단계: 카드 추천 버튼
# ──────────────────────────────────────
if st.session_state["recommendation"] is None:
    if st.button("카드 추천 받기", type="primary", use_container_width=True):
        if not persona_text.strip():
            st.warning("소비 패턴을 입력해주세요.")
        else:
            with st.spinner("AI가 맞춤 카드를 분석하고 있습니다..."):
                result = get_structured_recommendation(persona_text)
            st.session_state["recommendation"] = result
            st.session_state["persona"] = persona_text
            # 추천 결과를 대화 히스토리 초기값으로 저장
            rec_lines = []
            for r in result.get("recommendations", []):
                rec_lines.append(f"- {r.get('card_name','')} ({r.get('card_company','')}, {r.get('card_type','')}): {r.get('reason','')}")
            st.session_state["chat_messages"] = [
                {"role": "user", "content": persona_text},
                {"role": "assistant", "content": "위 카드들을 추천드렸습니다.\n" + "\n".join(rec_lines)},
            ]
            st.rerun()


# ──────────────────────────────────────
# 2단계: 추천 결과 + 후속 채팅
# ──────────────────────────────────────
if st.session_state["recommendation"] is not None:
    result = st.session_state["recommendation"]
    recommendations = result.get("recommendations", [])

    if not recommendations:
        st.error("추천 결과를 생성하지 못했습니다. 다시 시도해주세요.")
    else:
        credit_cards = [r for r in recommendations if r.get("card_type", "신용") == "신용"]
        check_cards = [r for r in recommendations if r.get("card_type") == "체크"]
        left_col, right_col = st.columns(2)
        with left_col:
            render_cards(credit_cards, "💳 신용카드 추천", "section-title-credit")
        with right_col:
            render_cards(check_cards, "🏦 체크카드 추천", "section-title-check")

    # ── 후속 대화 영역 ──
    st.markdown('<div class="chat-divider">💬 추천 결과에 대해 궁금한 점을 물어보세요</div>', unsafe_allow_html=True)

    # 이전 후속 대화 표시 (초기 추천 2개 제외)
    for msg in st.session_state["chat_messages"][2:]:
        if msg["role"] == "user":
            st.markdown(f'<div style="display:flex;justify-content:flex-end;"><div class="chat-bubble-user">{msg["content"]}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bubble-ai">{msg["content"]}</div>', unsafe_allow_html=True)

    # 스트리밍 응답 영역 (폼 위에 위치)
    streaming_area = st.empty()

    # 하단 여백 확보
    st.markdown('<div class="chat-bottom-spacer"></div>', unsafe_allow_html=True)

    # 하단 고정 채팅 입력
    with st.container():
        st.markdown('<div class="fixed-chat-form">', unsafe_allow_html=True)
        with st.form(key="chat_form", clear_on_submit=True):
            col1, col2 = st.columns([6, 1])
            with col1:
                follow_up = st.text_input(
                    "후속 질문",
                    placeholder="예: 연회비가 더 저렴한 카드는 없나요?",
                    label_visibility="collapsed",
                )
            with col2:
                submitted = st.form_submit_button("전송")
        st.markdown('</div>', unsafe_allow_html=True)

    if submitted and follow_up.strip():
        # 사용자 메시지 저장 + 표시
        st.session_state["chat_messages"].append({"role": "user", "content": follow_up})

        # AI 스트리밍 응답
        history = st.session_state["chat_messages"][:-1][-12:]
        stream, _ = get_chat_stream(follow_up, history)

        full_response = ""
        with streaming_area.container():
            st.markdown(f'<div style="display:flex;justify-content:flex-end;"><div class="chat-bubble-user">{follow_up}</div></div>', unsafe_allow_html=True)
            response_placeholder = st.empty()
            for chunk in stream:
                full_response += chunk
                response_placeholder.markdown(f'<div class="chat-bubble-ai">{full_response}▌</div>', unsafe_allow_html=True)
            response_placeholder.markdown(f'<div class="chat-bubble-ai">{full_response}</div>', unsafe_allow_html=True)

        st.session_state["chat_messages"].append({"role": "assistant", "content": full_response})
