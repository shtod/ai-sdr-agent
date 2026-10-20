"""SQL 线索字段定义与输出规范化。

字段与作业要求的 JSON 结构一一对应。
"""
import re

_NUM_RE = re.compile(r"\d+")

SQL_FIELDS = [
    "company_name",      # 企业抬头
    "industry",          # 行业
    "area",              # 地区
    "contact_name",      # 联系人
    "contact_title",     # 职位
    "phone",             # 手机号
    "intent_level",      # high|medium|low
    "intent_reason",     # 判断依据
    "demand_summary",    # 客户需求
    "mendian",           # 门店数
    "shejishi",          # 设计师人数
    "call_time",         # 通话时间
    "next_action",       # 建议下一步
    "confidence_score",  # 0.0~1.0
    "need_human_review", # true/false
]

# 允许的意向等级
INTENT_LEVELS = {"high", "medium", "low"}


def empty_record():
    """返回字段齐全的空记录。"""
    return {k: None for k in SQL_FIELDS}


def _to_float(v):
    try:
        return round(float(v), 3)
    except (TypeError, ValueError):
        return None


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "是")
    return bool(v)


def _extract_int(v):
    """从「5家」「30人」等描述中提取首个整数；无数字返回 None。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        m = _NUM_RE.search(v)
        return int(m.group()) if m else None
    return None


def normalize(record):
    """规范化一条记录：补齐字段、类型收敛、意向等级小写。"""
    out = empty_record()
    for k in SQL_FIELDS:
        if k in record:
            out[k] = record[k]

    # 类型收敛
    out["confidence_score"] = _to_float(out.get("confidence_score"))
    out["need_human_review"] = _to_bool(out.get("need_human_review"))
    if out.get("intent_level") is not None:
        out["intent_level"] = str(out["intent_level"]).strip().lower()
        if out["intent_level"] not in INTENT_LEVELS:
            out["intent_level"] = None

    # 空字符串统一视为 None，避免输出脏值
    for k in SQL_FIELDS:
        if isinstance(out[k], str) and out[k].strip() == "":
            out[k] = None

    # 门店数/设计师人数：尽量收敛为数字，无法提取则保留原描述
    for k in ("mendian", "shejishi"):
        num = _extract_int(out.get(k))
        if num is not None:
            out[k] = num
    return out
