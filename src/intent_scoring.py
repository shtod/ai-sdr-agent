"""第四步（难点 2）：客户意向度评分。

评分卡：LLM 先对每个维度打 0/1/2 分，代码做加权求和（确定性、可解释），
再映射到 high / medium / low。
"""
from config import (
    INTENT_DIMENSIONS,
    INTENT_HIGH_THRESHOLD,
    INTENT_MEDIUM_THRESHOLD,
)
from src import llm
from src.prompts import INTENT_PROMPT, SYSTEM_BASE, render

DIM_KEYS = [d["key"] for d in INTENT_DIMENSIONS]
WEIGHTS = {d["key"]: d["weight"] for d in INTENT_DIMENSIONS}
LABELS = {d["key"]: d["label"] for d in INTENT_DIMENSIONS}


def _clamp_score(v):
    """把 LLM 给的分收敛到 0~2。"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0
    return max(0.0, min(2.0, v))


def _level(weighted):
    if weighted >= INTENT_HIGH_THRESHOLD:
        return "high"
    if weighted >= INTENT_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _confidence(weighted):
    """意向置信度：取到最近等级分界线的距离（分类 margin）。

    越靠近 0.9 / 1.5 分界线越不确定；远离分界线（含两端极值）越确定。
    避免旧公式「只看到下限的距离」导致中意向被系统性高估。
    """
    margin = min(
        abs(weighted - b) for b in (INTENT_HIGH_THRESHOLD, INTENT_MEDIUM_THRESHOLD)
    )
    return round(min(1.0, max(0.4, 0.5 + margin)), 3)


def score_intent(text):
    """返回 dict: intent_level / intent_reason / scores / weighted / confidence。"""
    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": render(INTENT_PROMPT, system=SYSTEM_BASE, text=text)},
    ]
    data = llm.chat_json(messages)
    if not isinstance(data, dict):
        data = {}

    raw_scores = data.get("scores") or {}
    evidence = data.get("evidence") or {}

    scores = {k: _clamp_score(raw_scores.get(k)) for k in DIM_KEYS}
    weighted = sum(scores[k] * WEIGHTS[k] for k in DIM_KEYS)
    level = _level(weighted)

    # 依据拼成可读文本，逐维度列出，便于人工复核
    reason_parts = []
    for k in DIM_KEYS:
        reason_parts.append(
            f"{LABELS[k]}({WEIGHTS[k]:.2f})={scores[k]:.0f}分: {evidence.get(k) or '无'}"
        )
    reason = "；".join(reason_parts)

    # 置信度：分类 margin 越大越确定（见 _confidence）
    confidence = _confidence(weighted)

    return {
        "intent_level": level,
        "intent_reason": reason,
        "scores": scores,
        "weighted": round(weighted, 3),
        "confidence": confidence,
    }
