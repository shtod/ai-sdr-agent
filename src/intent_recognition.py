"""第零步：意图识别。判断是否为有效销售线索对话 + 对话类型。"""
from src import llm
from src.prompts import INTENT_RECOGNITION_PROMPT, SYSTEM_BASE, render


def recognize(text):
    """返回 dict: is_valid_lead / conversation_type / reason。"""
    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": render(INTENT_RECOGNITION_PROMPT, system=SYSTEM_BASE, text=text)},
    ]
    data = llm.chat_json(messages)
    if not isinstance(data, dict):
        data = {}
    return {
        "is_valid_lead": bool(data.get("is_valid_lead", True)),
        "conversation_type": data.get("conversation_type") or "unknown",
        "reason": data.get("reason") or "",
    }
