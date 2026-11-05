"""Streamlit 网页版出行助手"""

import streamlit as st
from agent import run_agent, SYSTEM_PROMPT

st.set_page_config(page_title="出行助手", page_icon="🌦️")
st.title("🌦️ 出行助手")

# 每个浏览器标签页一份独立的对话历史（方案 A 的状态就存在这里）
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# 渲染历史（system 不给用户看）
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# 底部输入框：用户按下回车，prompt 才有值
if prompt := st.chat_input("问点啥？比如：北京天气怎么样"):
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            reply = run_agent(prompt, st.session_state.messages)
        st.write(reply)