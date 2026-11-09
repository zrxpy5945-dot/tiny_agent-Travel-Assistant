"""命令行入口"""

from agent import run_agent, SYSTEM_PROMPT
from memory import build_system_prompt, extract_facts, save_memory

if __name__ == "__main__":
    print("多轮对话已开启，输入 exit 或直接回车退出。\n")
    messages = [{"role": "system", "content": build_system_prompt(SYSTEM_PROMPT)}]
    while True:
        question = input("你：")
        if question.strip().lower() in ("exit", "quit", ""):
            added, removed = extract_facts(messages)
            if added or removed:
                save_memory(added, removed)
                print(f"已记住 {len(added)} 条信息，清理 {len(removed)} 条过时信息。")
            print("再见，老大。")
            break
        print(run_agent(question, messages))
        print()
