"""命令行入口"""

from agent import run_agent,SYSTEM_PROMPT

if __name__ == "__main__":
    print("多轮对话已开启，输入 exit 或直接回车退出。\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        question = input("你：")
        if question.strip().lower() in ("exit", "quit", ""):
            print("再见，老大。")
            break
        print(run_agent(question, messages))
        print()