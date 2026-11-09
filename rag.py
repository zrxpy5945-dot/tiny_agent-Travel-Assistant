"""极简 RAG：本地知识库切块 + 关键词检索"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import jieba

jieba.setLogLevel(logging.WARNING)  # 关掉分词器的调试日志

BASE_DIR = Path(__file__).parent
DOC_DIR = BASE_DIR / "data" / "knowledge"
INDEX_FILE = BASE_DIR / "index.json"

CHUNK_SIZE = 350  # 每块目标字数

# 城市 -> 该城市专属的知识文档。查询点名了某城市时，只在这些文档里检索，
# 避免"预约""景点"这类通用词把别的城市的文档也捞出来。
CITY_DOCS = {
    "北京": "北京出行常识.md",
    "成都": "成都周边.md",
}


def load_docs() -> list:
    """读取 knowledge 目录下所有 markdown，返回 [(文件名, 全文)]"""
    if not DOC_DIR.exists():
        return []
    docs = []
    for path in sorted(DOC_DIR.glob("*.md")):
        docs.append((path.name, path.read_text(encoding="utf-8")))
    return docs


def split_chunks(text: str, size: int = CHUNK_SIZE) -> list:
    """按空行切段落，再把相邻段落合并到接近 size 字。"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if not current:
            current = para
        elif len(current) + len(para) <= size:
            current = current + "\n" + para
        else:
            chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def build_index() -> list:
    """扫全部文档，切成块，写入 index.json。"""
    chunks = []
    for name, text in load_docs():
        for piece in split_chunks(text):
            chunks.append({"source": name, "text": piece})
    INDEX_FILE.write_text(
        json.dumps(
            {
                "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "chunks": chunks,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return chunks


def _load_chunks() -> list:
    """读索引，不存在就先建一次。"""
    if not INDEX_FILE.exists():
        return build_index()
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))["chunks"]
    except (json.JSONDecodeError, KeyError, OSError):
        return build_index()


def _tokenize(text: str) -> list:
    """中文分词，丢掉单字和一些无意义的词，减少噪声。"""
    words = [w.strip() for w in jieba.lcut(text)]
    return [w for w in words if len(w) >= 2]


def search(query: str, top_k: int = 3) -> list:
    """关键词打分检索，返回 top_k 个片段（score > 0 才算命中）。"""
    chunks = _load_chunks()
    q_words = _tokenize(query)
    if not q_words or not chunks:
        return []

    # 查询里点名了哪些城市 -> 这些城市对应的专属文档
    wanted_docs = {doc for city, doc in CITY_DOCS.items() if city in query}
    city_docs = set(CITY_DOCS.values())

    results = []
    for chunk in chunks:
        source = chunk["source"]
        # 点名了城市时，跳过其它城市的专属文档；通用文档（如火车票规则）不受限制
        if wanted_docs and source in city_docs and source not in wanted_docs:
            continue
        text = chunk["text"]
        score = 0
        for word in q_words:
            count = text.count(word)
            if count:
                score += 1 + count  # 出现一次算基础分，多次出现略加权
        if score:
            # 长块天然更容易命中，用长度开根号稀释一下
            results.append((score / (len(text) ** 0.5), chunk))

    results.sort(key=lambda item: item[0], reverse=True)
    return [
        {"source": chunk["source"], "text": chunk["text"], "score": round(score, 2)}
        for score, chunk in results[:top_k]
    ]


if __name__ == "__main__":
    args = sys.argv[1:]

    if args and args[0] == "--build":
        chunks = build_index()
        print(f"索引完成：{len(chunks)} 个块 -> {INDEX_FILE}")
    else:
        query = " ".join(args) if args else input("查询：")
        hits = search(query)
        if not hits:
            print("没有找到相关内容")
        for hit in hits:
            preview = hit["text"].replace("\n", " ")[:110]
            print(f"\n[{hit['score']}] {hit['source']}")
            print(f"  {preview} ...")
