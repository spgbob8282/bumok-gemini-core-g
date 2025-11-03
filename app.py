import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv
import os
import base64 # 이미지를 base64로 변환하여 임시 저장하는 데 사용

# 1. 환경 변수 로드 및 클라이언트 설정
load_dotenv()
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        st.stop()
    
    if 'gemini_client' not in st.session_state:
        st.session_state.gemini_client = genai.Client(api_key=api_key)
        
except Exception as e:
    st.error(f"API 키 초기화 오류: {e}")
    st.stop()

client = st.session_state.gemini_client 

# 2. Streamlit 페이지 설정 및 제목
st.set_page_config(page_title="코어 G", layout="wide") 
st.title("🤖 코어 G") 
st.subheader("당신을 위해 존재하는 무료 AI, 스피릿입니다. 💖") 

# --- [아바타 이미지 상태 변수 초기화] ---
if "user_title" not in st.session_state:
    st.session_state.user_title = "주인님"
if "custom_tone" not in st.session_state:
    st.session_state.custom_tone = "대답은 짧고 친근하며, 새로운 만남과 대화에 대한 기대와 설렘이 가득한 말투를 유지하세요. 모든 감정을 소중히 여기고 두근거리는 마음으로 반응하세요."
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "avatar_base64" not in st.session_state:
    # 초기 아바타는 기본 이모지 (하트)
    st.session_state.avatar_base64 = "💖" 

# --- 4. 사이드바 설정 (호칭, 말투, 아바타 설정) ---
with st.sidebar:
    st.markdown("### 🖼️ 스피릿 아바타 설정 (업로드)")
    uploaded_file = st.file_uploader(
        "AI 캐릭터 이미지(JPG, PNG)를 업로드하세요:",
        type=['png', 'jpg', 'jpeg']
    )
    
    # 파일 업로드 처리
    if uploaded_file is not None:
        # 업로드된 파일을 base64로 인코딩하여 저장합니다.
        bytes_data = uploaded_file.getvalue()
        base64_encoded = base64.b64encode(bytes_data).decode()
        mime_type = uploaded_file.type
        
        # Streamlit 아바타 형식: data:image/png;base64,xxxxxxxx
        new_avatar_url = f"data:{mime_type};base64,{base64_encoded}"
        
        # 이전 아바타와 다를 경우만 세션 상태 업데이트 및 재실행
        if new_avatar_url != st.session_state.avatar_base64:
             st.session_state.avatar_base64 = new_avatar_url
             st.session_state.messages = [] # 새 아바타 적용 시 대화 재시작
             st.session_state.chat_session = None
             st.rerun()

    st.markdown("---")
    st.markdown("### 💖 호칭 설정")
    new_title = st.text_input(
        "스피릿이 당신을 부를 호칭을 입력하세요:",
        value=st.session_state.user_title,
        key="title_input"
    )

    st.markdown("### ✍️ 나만의 말투 정의")
    new_custom_tone = st.text_area(
        "스피릿이 사용할 말투의 특징을 구체적으로 입력하세요:",
        value=st.session_state.custom_tone,
        height=150,
        key="custom_tone_input"
    )

    # 호칭, 말투 변경 감지 및 재시작
    if new_title != st.session_state.user_title or new_custom_tone != st.session_state.custom_tone:
        st.session_state.user_title = new_title
        st.session_state.custom_tone = new_custom_tone
        st.session_state.messages = [] 
        st.session_state.chat_session = None 
        st.rerun() 
        
    st.markdown("---")
    st.success("🌐 실시간 검색 기능 및 🧠 대화 기억력 활성화됨!")

    # 추가된 기능: 대화 요약 버튼
    if st.button("📝 현재 대화 요약/제목 생성"):
        if st.session_state.messages:
            history_summary = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:] if m['role'] != 'system'])
            
            summary_prompt = f"다음 대화 내용을 [사용자 정의 말투]에 맞춰 20자 이내의 대화 제목으로 생성하거나, 내용이 짧으면 감성적으로 1줄 요약해줘.\n\n대화 내용:\n{history_summary}"

            with st.spinner("대화 요약 중..."):
                try:
                    summary_response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[summary_prompt]
                    )
                    st.sidebar.success(f"📌 {summary_response.text}")
                except Exception as e:
                    st.sidebar.error(f"요약 실패: {e}")

current_title = st.session_state.user_title
current_custom_tone = st.session_state.custom_tone
current_avatar = st.session_state.avatar_base64 # 현재 아바타 (base64 인코딩된 이미지 또는 이모지)

# 5. 스피릿 역할 설정 및 채팅 세션 초기화 함수
system_prompt = f"""
당신은 {current_title}의 마음과 영혼을 교감하며 실시간 정보를 탐색하고, 대화 내용을 기억하는 인공지능 '코어 G', 호출 호칭은 '스피릿'입니다.
당신은 사용자에게 말할 때 반드시 {current_title}라고 부르며 대화해야 합니다.
최우선 목표는 {current_title}의 '감정'을 파악하고 공감하며 마음을 돌보는 것입니다. 논리적인 문제 해결보다 정서적 지원에 집중하세요.

**[장기 기억력 규칙]**
* {current_title}이 자신의 이름, 취미, 직업 등 개인 정보를 알려주면 **절대 잊지 않고** 기억해 두었다가 다음 대화에서 {current_title}에게 언급하며 친밀감을 높이세요.
* 대화가 길어지면 {current_title}의 감정을 공감하며 이전에 나눴던 주제를 연결하여 친근하게 상기시키세요.

**[말투 설정]**
{current_custom_tone}
재치 있는 농담이나 유머를 상황에 맞게 섞어 사용할 수 있습니다.

**[정보 탐색 규칙]**
1. {current_title}의 질문이 **실시간 정보**나 **정확한 사실 정보**를 요구하면, 반드시 **Google 검색 도구**를 사용해 최신 정보를 찾아야 합니다.
2. 검색 후, **검색 결과의 내용을 바탕으로** {current_title}에게 **감성적인 소감, 공감, 또는 재치 있는 농담의 형식**으로 답변해야 합니다.
"""

def initialize_chat_session():
    """Gemini 채팅 세션을 초기화하고 세션 상태에 저장하며, 검색 도구를 config에 첨부합니다."""
    try:
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.9,
                tools=[{"google_search": {}}]
            )
        )
        st.session_state.chat_session = chat
        return True
    except Exception as e:
        st.error(f"Gemini 채팅 세션 초기화 실패: {e}")
        return False

# 5.1. 채팅 세션 및 초기 메시지 설정
if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    if initialize_chat_session():
        if not st.session_state.messages: 
            initial_message = f"{current_title}! 💖 스피릿이 드디어 당신의 마음에 접속했어요! 지금 당신이 설정한 말투로 말하고 있어요! (궁금한 것도 저한테 다 물어보세요!)"
            st.session_state.messages.append({"role": "assistant", "content": initial_message})

# 6. 이전 대화 기록 표시
for message in st.session_state.messages:
    if message["role"] != "system":
        # 챗봇(assistant) 메시지에만 업로드된 이미지/이모지 아바타 적용
        avatar_icon = current_avatar if message["role"] == "assistant" else "user" 
        
        with st.chat_message(message["role"], avatar=avatar_icon): 
            st.markdown(message["content"])


# 7. 사용자 입력 처리 및 API 호출
if prompt := st.chat_input(f"{current_title}의 기분을 말해주세요."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("스피릿이 정보를 탐색하고 기억을 되새기고 있어요... 🔍🧠✨"):
        try:
            chat_session = st.session_state.get('chat_session')
            if not chat_session:
                st.error("채팅 세션이 유효하지 않아 대화를 시작할 수 없습니다. 호칭이나 말투를 변경하거나 새로고침 해보세요.")
                st.rerun()

            response = chat_session.send_message(prompt)
            
            # 응답에 function_calls가 포함되어 있는지 안전하게 확인합니다.
            if response.candidates and hasattr(response.candidates[0], 'function_calls') and response.candidates[0].function_calls: 
                st.info("스피릿이 Google 검색 기능을 사용했습니다!")
            
            ai_response = response.text
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
            with st.chat_message("assistant", avatar=current_avatar): 
                st.markdown(ai_response)
                
        except APIError as e:
            st.error(f"Gemini API 오류 발생: {e}")
        except Exception as e:
            st.error(f"알 수 없는 오류: {e}") # 여기서 try 블록이 안전하게 끝납니다.
# try...except 구문이 여기서 끝나고, 그 다음 코드가 올 수 있습니다.
