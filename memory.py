"""跨对话记忆：抽取用户的长期信息并持久化到本地 JSON"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "memory.json"
MAX_FACTS = 20  # 最多保留 20 条，防止无限增长

_EXTRACT_PROMPT = (
    "从下面这段对话中提取关于用户的、长期有效的信息，例如常住城市、出行偏好、"
    "生活习惯、身体状况。不要提取一次性的问题。\n"
    "只输出 JSON 数组，每个元素是一句简短的中文描述，例如 "
    '["用户常住北京", "用户怕冷，冬天需要加厚外套"]。\n'
    "如果没有值得记住的信息，输出 []。不要输出任何其它文字。\n\n对话：\n"
)


def load_memory() -> dict:
    """读取记忆文件，不存在或损坏时返回空记忆。"""
    if not MEMORY_FILE.exists():
        return {"facts": [], "updated_at": ""}
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"facts": [], "updated_at": ""}
    return {"facts": data.get("facts", []), "updated_at": data.get("updated_at", "")}


def merge_facts(old: list, new: list) -> list:
    """新旧事实合并去重，只保留最近 MAX_FACTS 条。"""
    seen = set()
    merged = []
    for fact in list(old) + list(new):
        fact = str(fact).strip()
        if fact and fact not in seen:
            seen.add(fact)
            merged.append(fact)
    return merged[-MAX_FACTS:]


def save_memory(facts: list) -> None:
    """把新事实合并进记忆文件。"""
    merged = merge_facts(load_memory()["facts"], facts)
    MEMORY_FILE.write_text(
        json.dumps(
            {
                "facts": merged,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def build_system_prompt(base_prompt: str) -> str:
    """把已记住的用户信息拼到 system prompt 后面。"""
    facts = load_memory()["facts"]
    if not facts:
        return base_prompt
    lines = "\n".join(f"{i}. {fact}" for i, fact in enumerate(facts, 1))
    return f"{base_prompt}\n\n【已知用户信息，回答时请结合】\n{lines}"


def extract_facts(messages: list) -> list:
    """调用一次 LLM 从对话里抽取长期事实，失败时返回空列表。"""
    from agent import client, MODEL  # 延迟导入，避免循环依赖

    dialogue = "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}：{m['content']}"
        for m in messages
        if isinstance(m, dict)
        and m.get("role") in ("user", "assistant")
        and m.get("content")
    )
    if not dialogue:
        return []

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": _EXTRACT_PROMPT + dialogue}],
            temperature=0,
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as e:  # 抽取失败不能影响正常退出
        print(f"  [记忆抽取失败，已跳过] {e}")
        return []

    # 模型有时会包一层 ```json 代码块，去掉再解析
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        facts = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(facts, list):
        return []
    return [str(f).strip() for f in facts if str(f).strip()]
