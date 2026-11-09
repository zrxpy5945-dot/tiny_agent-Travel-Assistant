"""Streamlit 网页版出行助手"""

import streamlit as st

from agent import run_agent, SYSTEM_PROMPT
from memory import build_system_prompt, extract_facts, load_memory, save_memory

st.set_page_config(page_title="出行助手", page_icon="🌦️")
st.title("🌦️ 出行助手")

# 每个浏览器标签页一份独立的对话历史，开局注入已记住的用户信息
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": build_system_prompt(SYSTEM_PROMPT)}
    ]

# 展示已记住的信息 + 手动记忆按钮（网页没有"退出"事件，只能靠按钮触发）
facts = load_memory()["facts"]
if facts:
    with st.expander(f"🧠 已记住的 {len(facts)} 条用户信息"):
        for fact in facts:
            st.write(f"- {fact}")

if st.button("📌 记住这次对话"):
    added, removed = extract_facts(st.session_state.messages)
    if added or removed:
        save_memory(added, removed)
        st.success(
            f"已记住 {len(added)} 条信息，清理 {len(removed)} 条过时信息，刷新页面后生效"
        )
    else:
        st.info("这次对话没有值得记住的新信息")

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
