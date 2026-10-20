"""第三步（难点 1）：企业抬头识别与还原。

方案（不用外部企业库 API）：
  候选提取 + 行业词库三层匹配（精确 / 长度门控编辑距离 / 拼音同音）
      ->  大模型结合上下文 + 词库命中结果，推理还原全称 + 置信度
"""
import json
import re
from pathlib import Path

from src import llm
from src.prompts import COMPANY_PROMPT, SYSTEM_BASE, render

LEXICON_PATH = Path(__file__).resolve().parent.parent / "data" / "lexicon" / "company_lexicon.json"

# 规范化时去掉的标点/空白
_PUNCT_RE = re.compile(r"[\s\"'“”‘’「」『』（）()、，。·\-—]")


def load_lexicon():
    """加载行业词库，返回 [{"alias":..., "full_name":..., "note":...}, ...]。"""
    try:
        with open(LEXICON_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("aliases", [])
    except (OSError, json.JSONDecodeError):
        return []


def _norm(s):
    """规范化：去标点空白、转小写。"""
    return _PUNCT_RE.sub("", str(s).lower())


def _edit_distance(a, b):
    """莱文斯坦编辑距离（纯 Python 实现，用于容错转写错字）。"""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _fuzzy_in(norm_text, cand, max_distance=1):
    """cand 是否以「近似形式」（编辑距离 <= max_distance）出现在 norm_text 中。"""
    length = len(cand)
    if length == 0 or length > len(norm_text):
        return False
    for i in range(len(norm_text) - length + 1):
        if _edit_distance(norm_text[i:i + length], cand) <= max_distance:
            return True
    return False


def _fuzzy_budget(cand):
    """字符级模糊匹配的编辑距离预算：候选越长容错越多。

    2 字别名不做字符级模糊（编辑距离 1 意味着 50% 容错，会把「我们/价格/品牌」
    误命中成「我乐/玛格/金牌」）；3~4 字容错 1 字；5 字以上容错 2 字。
    """
    n = len(cand)
    if n >= 5:
        return 2
    if n >= 3:
        return 1
    return 0


def _pinyin(s):
    """返回无调拼音串，用于容错转写/ASR 同音错字；pypinyin 不可用时返回 None。"""
    try:
        from pypinyin import lazy_pinyin

        return "".join(lazy_pinyin(s))
    except Exception:  # noqa: BLE001 依赖缺失则降级为不做拼音匹配
        return None


def match_lexicon(text, lexicon):
    """词库匹配（难点 1 候选召回）。

    三层策略（由严到宽，降低误召回）：
    1) 精确包含：原文含别名或全称；
    2) 字符级模糊：仅对 >=3 字的候选做编辑距离容错（「索非亚」→「索菲亚」）；
    3) 拼音同音匹配：>=2 字候选的拼音串相等，覆盖 ASR/转写同音错字（「欧排」→「欧派」）。
    """
    norm_text = _norm(text)
    text_pinyin = _pinyin(norm_text)
    hits = []
    for item in lexicon:
        matched = False
        for cand in (item.get("alias", ""), item.get("full_name", "")):
            if not cand:
                continue
            nc = _norm(cand)
            if not nc:
                continue
            # 1) 精确包含
            if nc in norm_text:
                matched = True
                break
            # 2) 字符级模糊（仅 >=3 字）
            budget = _fuzzy_budget(nc)
            if budget >= 1 and _fuzzy_in(norm_text, nc, budget):
                matched = True
                break
            # 3) 拼音同音（>=2 字）
            if len(nc) >= 2 and text_pinyin:
                cp = _pinyin(nc)
                if cp and cp in text_pinyin:
                    matched = True
                    break
        if matched:
            hits.append(item)
    return hits


def resolve_company(text):
    """还原企业全称，返回 dict: company_name / alias / confidence / reason / lexicon_hits。"""
    lexicon = load_lexicon()
    hits = match_lexicon(text, lexicon)
    lexicon_desc = json.dumps(hits, ensure_ascii=False) if hits else "（无命中）"

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": render(COMPANY_PROMPT, system=SYSTEM_BASE, text=text, lexicon=lexicon_desc)},
    ]
    data = llm.chat_json(messages)
    if not isinstance(data, dict):
        data = {}

    data.setdefault("lexicon_hits", [h.get("full_name") or h.get("alias") for h in hits])
    return data
