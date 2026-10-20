"""第一步：结构化信息抽取。"""
from src import llm, preprocess
from src.prompts import EXTRACT_PROMPT, SYSTEM_BASE, render

# 从抽取结果里并入最终记录的字段（排除难点字段，由专门步骤处理）
EXTRACT_FIELDS = [
    "industry",
    "area",
    "contact_name",
    "contact_title",
    "phone",
    "mendian",
    "shejishi",
    "demand_summary",
    "call_time",
    "next_action",
]


def extract_fields(text):
    """调用 LLM 抽取基础字段，返回 dict；失败返回空 dict。"""
    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": render(EXTRACT_PROMPT, system=SYSTEM_BASE, text=text)},
    ]
    data = llm.chat_json(messages)
    if not isinstance(data, dict):
        return {}

    # 手机号：优先用正则兜底，LLM 未给出时补上
    if not data.get("phone"):
        data["phone"] = preprocess.extract_phone(text)
    return data
