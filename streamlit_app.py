import streamlit as st
import logging
from PIL import Image, ImageEnhance
import time
import json
import requests
import base64
import uuid

logging.basicConfig(level=logging.INFO)

NUMBER_OF_MESSAGES_TO_DISPLAY = 20
API_DOCS_URL = "https://docs.alpha-finance.com"


st.set_page_config(
    page_title="AlphaFinance Assistant",
    page_icon="static/vv-b-logo.png",
    layout="wide",
    initial_sidebar_state="auto"
)

def img_to_base64(image_path):
    """Convert image to base64."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        logging.error(f"Error converting image to base64: {str(e)}")
        return None
    
API_URL = "http://localhost:8003"


if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = []

def send_message(message_text):
    """Send message to API and get response"""
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={"session_id": st.session_state.session_id, "message": message_text}
        )
        return response.json()["response"]
    except Exception as e:
        st.error(f"Error communicating with the API: {str(e)}")
        return None

@st.cache_data(show_spinner=False)
def long_running_task(duration):
    """Simulates a long-running operation."""
    time.sleep(duration)
    return "Long-running operation completed."

@st.cache_data(show_spinner=False)
def load_and_enhance_image(image_path, enhance=False):
    """Load and optionally enhance an image."""
    img = Image.open(image_path)
    if enhance:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)
    return img

def initialize_conversation():
    """Initialize the conversation history with system and assistant messages."""
    assistant_message = "Hello! I am AlphaFinance. How can I assist you with Finance today?"
    conversation_history = [
        {"role": "assistant", "content": assistant_message}
    ]
    return conversation_history

def on_chat_submit(chat_input):
    """Handle chat input submissions and interact with the API."""
    user_input = chat_input.strip().lower()
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = initialize_conversation()
    st.session_state.conversation_history.append({"role": "user", "content": user_input})
    assistant_reply = send_message(user_input)
    st.session_state.conversation_history.append({"role": "assistant", "content": assistant_reply})
    st.session_state.history.append({"role": "user", "content": user_input})
    st.session_state.history.append({"role": "assistant", "content": assistant_reply})

def initialize_session_state():
    """Initialize session state variables."""
    if "history" not in st.session_state:
        st.session_state.history = []
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

def main():
    """Display chat interface and handle user interactions."""
    initialize_session_state()
    if not st.session_state.history:
        initial_bot_message = "👋 Hello! How can I assist you with Finance today?"
        st.session_state.history.append({"role": "assistant", "content": initial_bot_message})
        st.session_state.conversation_history = initialize_conversation()
    e
    img_path = "static/vv-b-logo.png"
    img_base64 = img_to_base64(img_path)
    if img_base64:
        st.sidebar.markdown(
            f'<img src="data:image/png;base64,{img_base64}" class="cover-glow">',
            unsafe_allow_html=True,
        )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Features:")
    st.sidebar.markdown("- 📊 Financial Analysis")
    st.sidebar.markdown("- 📈 Market Trends")
    st.sidebar.markdown("- 💡 Investment Insights")
    st.sidebar.markdown("- 📉 Economic Indicators")
    st.sidebar.markdown("---")
    
    chat_input = st.chat_input("💭 Ask me about financial trends or market insights...")
    if chat_input:
        on_chat_submit(chat_input)
    
    # Display chat history
    for message in st.session_state.history[-NUMBER_OF_MESSAGES_TO_DISPLAY:]:
        role = message["role"]
        avatar_user = "static/user.png"
        avatar_bot = "static/bot.png"
        background_color = "#e3f2fd" if role == "assistant" else "#d1e7dd"
        align_style = "flex-start" if role == "assistant" else "flex-end"
        avatar_image = avatar_bot if role == "assistant" else avatar_user
        
        avatar_base64 = img_to_base64(avatar_image)
        avatar_html = f'<img src="data:image/png;base64,{avatar_base64}" width="40" style="border-radius: 50%; margin: 5px;">' if avatar_base64 else ""
        
        st.markdown(
            f'<div style="display: flex; justify-content: {align_style}; margin-bottom: 10px; align-items: center;">'
            f'  {avatar_html if role == "assistant" else ""}'
            f'  <div style="background-color: {background_color}; padding: 10px; border-radius: 10px; max-width: 70%; display: flex; align-items: center;">'
            f'    <span>{message["content"]}</span>'
            f'  </div>'
            f'  {avatar_html if role == "user" else ""}'
            f'</div>',
            unsafe_allow_html=True
        )
                
if __name__ == "__main__":
    main()
