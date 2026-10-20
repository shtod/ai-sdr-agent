"""AI SDR Agent 主流程：编排各步骤，输出结构化 SQL 线索。

流水线（对齐文档要求）：
  0. 意图识别（intent_recognition）
  1. 信息抽取（extract）
  2. 企业抬头还原（company_resolution，难点 1）
  3. 意向度评分（intent_scoring，难点 2）
  4. 组装 + 置信度 + 人工复核标记
"""
from config import REVIEW_THRESHOLD
from src import company_resolution, extract, intent_recognition, intent_scoring, schema
from src.preprocess import extract_phone


def _float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def run(text):
    """输入电话沟通记录文本，输出规范化 SQL 线索 dict。

    顶层为作业要求的 SQL 字段，附加 `_meta` 记录各步骤中间过程（用于工具展示与讲解）。
    """
    # Step 0：意图识别
    intent_rec = intent_recognition.recognize(text)

    # Step 1：信息抽取
    fields = extract.extract_fields(text)

    # Step 2：企业抬头还原（难点 1）
    company = company_resolution.resolve_company(text)

    # Step 3：意向度评分（难点 2）
    intent = intent_scoring.score_intent(text)

    # Step 4：组装
    record = schema.empty_record()
    for k in extract.EXTRACT_FIELDS:
        record[k] = fields.get(k)
    record["company_name"] = company.get("company_name")
    record["intent_level"] = intent.get("intent_level")
    record["intent_reason"] = intent.get("intent_reason")
    if not record["phone"]:
        record["phone"] = extract_phone(text)

    company_conf = _float(company.get("confidence"), 0.5)
    intent_conf = _float(intent.get("confidence"), 0.5)

    # 非有效线索：强制 low + 需人工复核
    if not intent_rec["is_valid_lead"]:
        record["intent_level"] = "low"
        record["intent_reason"] = "非有效销售线索：" + (
            intent_rec["reason"] or "对话未体现采购意向"
        )
        intent_conf = min(intent_conf, 0.3)

    overall = round(min(company_conf, intent_conf), 3)
    record["confidence_score"] = overall
    record["need_human_review"] = bool(
        overall < REVIEW_THRESHOLD
        or company_conf < REVIEW_THRESHOLD
        or not intent_rec["is_valid_lead"]
    )

    record = schema.normalize(record)
    record["_meta"] = {
        "conversation_type": intent_rec["conversation_type"],
        "is_valid_lead": intent_rec["is_valid_lead"],
        "intent_recognition_reason": intent_rec["reason"],
        "company_alias": company.get("alias"),
        "company_reason": company.get("reason"),
        "company_confidence": company_conf,
        "company_lexicon_hits": company.get("lexicon_hits"),
        "intent_scores": intent.get("scores"),
        "intent_weighted": intent.get("weighted"),
        "intent_confidence": intent_conf,
    }
    return record
