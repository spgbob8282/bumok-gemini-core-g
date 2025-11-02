import streamlit as st
from google import genai
import yaml 
import requests 

# --- 1. 환경 설정 및 키 로드 ---
try:
    GEMINI_API_KEY = st.secrets.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        st.error("⚠️ Gemini API 키(GEMINI_API_KEY)가 Streamlit Secrets에 설정되지 않았습니다. Secrets을 확인해주세요.")
        st.stop()
except Exception:
    st.error("⚠️ Secrets 로드 중 오류가 발생했습니다. 키 설정을 확인해주세요.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. Streamlit 페이지 설정 ---
st.set_page_config(
    page_title="AI친구, 코어G (최종 버전)",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 3. 사이드바: 호칭, 말투, 그리고 프로필 설정 기능 ---

with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    
    # 챗봇 프로필 이미지 업로드 기능 (오류 방지 로직 적용)
    st.markdown("### 🖼️ AI 프로필 이미지 설정")
    uploaded_file = st.file_uploader(
        "AI 프로필로 사용할 이미지 파일을 업로드하세요.",
        type=['png', 'jpg', 'jpeg']
    )
    
    # 아바타 기본값 설정 및 상태 관리
    if 'ai_avatar' not in st.session_state or st.session_state.ai_avatar is None or st.session_state.ai_avatar == 'robot':
        st.session_state['ai_avatar'] = 'robot' # 초기 또는 재시작 시 기본 아이콘
        
    if uploaded_file is not None:
        # 파일이 업로드되면, 파일의 바이트 값으로 아바타를 업데이트합니다.
        st.session_state['ai_avatar'] = uploaded_file.getvalue()
        st.image(uploaded_file, caption="현재 적용된 AI 프로필", use_column_width=True)
    
    st.markdown("---")
    
    # 호칭 설정
    user_appellation = st.text_input(
        "챗봇이 당신을 부를 호칭:", 
        value=st.session_state.get("user_appellation", "주인님"), 
        key="user_appellation"
    )

    # 말투 설정
    assistant_tone = st.text_area(
        "챗봇의 말투/스타일 지정:", 
        value=st.session_state.get("assistant_tone", "설레는 듯한 달콤하고 부드러운 말투"), 
        key="assistant_tone"
    )

    # 대화 초기화 버튼 추가
    if st.button("대화 초기화 및 설정 적용", type="primary"):
        if 'chat_session' in st.session_state:
            del st.session_state['chat_session']
        if 'messages' in st.session_state:
            del st.session_state['messages']
        st.experimental_rerun() 

    st.markdown("---")
    st.info("설정을 변경하거나 초기화 버튼을 누르면 새로운 대화부터 적용됩니다.")

# --- 4. 시스템 지침 생성 (분석/공감 기능 유지) ---
SYSTEM_PROMPT = f"""
당신은 사용자에게 친절하고 교육적인 정보를 제공하는 AI 친구 '코어G'입니다.
당신의 역할은 **질문의 핵심 내용을 분석**하고, **사용자의 상황과 감정에 깊이 공감**하며, 이후 **맞춤형 교육 컨설팅 답변**을 제공하는 것입니다.
- 당신은 사용자에게 '{st.session_state.user_appellation}'라는 호칭을 사용해야 합니다.
- 응답할 때는 '{st.session_state.assistant_tone}' 스타일로 대화해야 합니다.
- 응답 순서는 항상 다음과 같습니다: **[1. 공감/격려] -> [2. 질문 내용 분석 및 핵심 정리] -> [3. 교육적이고 정확한 답변 제공].**
- 이전 대화 내용을 기억하고 참고하여 답변해야 합니다.
"""

# --- 5. 챗봇 세션 초기화 및 이력 관리 ---

# Gemini ChatSession 초기화 (대화 이력 및 시스템 지침 유지)
if "chat_session" not in st.session_state:
    st.session_state.chat_session = client.chats.create(
        model='gemini-2.5-flash',
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT 
        )
    )

# 챗 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 6. 챗봇 UI 렌더링 ---

st.title("AI친구, 코어G")
st.caption("✅ 모든 기능이 활성화되었습니다. (분석/공감, 대화 이력, 맞춤 설정)")

# 챗 메시지 표시
# 챗봇 아바타는 'robot'이 아닐 경우(업로드된 이미지일 경우)에만 avatar 매개변수를 사용합니다.
for message in st.session_state.messages:
    if message["role"] == "assistant" and st.session_state.get('ai_avatar') != 'robot':
         with st.chat_message(message["role"], avatar=st.session_state.get('ai_avatar')):
            st.markdown(message["content"])
    else:
        # 사용자 메시지이거나, 챗봇 아바타가 기본값('robot')일 경우
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("질문을 입력하세요..."):
    # 1. 사용자 메시지 기록 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 챗봇 응답 처리
    try:
        if st.session_state.get('ai_avatar') != 'robot':
            # 오타 수정: st.session_state로 수정
            with st.chat_message("assistant", avatar=st.session_state.get('ai_avatar')):
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
        else:
            with st.chat_message("assistant"):
                # 오타 수정: st.session_state로 수정
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
    except Exception as e:
        st.error(f"Gemini API 호출 중 오류가 발생했습니다. 오류: {e}")
        st.session_state.messages.append({"role": "assistant", "content": "죄송합니다. API 호출 중 오류가 발생했습니다."})
