"""一次性迁移：用新的意向置信度公式重算已有线索的置信度与复核标记。

背景：评分公式（src/intent_scoring.py 的 _confidence）更新后，新入库线索会用新公式；
此脚本把「改公式前」入库的旧线索重算一遍，不重新调用 LLM，只依据已存的
加权分（_meta.intent_weighted）与公司抬头置信度（_meta.company_confidence）。

用法：python rescore_leads.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db
from config import REVIEW_THRESHOLD
from src.intent_scoring import _confidence


def rescore(result):
    """依据已存 _meta 重算 (overall_conf, need_review)，与 src/agent.py 保持一致。"""
    meta = result.get("_meta") or {}
    valid = bool(meta.get("is_valid_lead", True))
    company_conf = float(meta.get("company_confidence") or 0.5)

    weighted = meta.get("intent_weighted")
    intent_conf = _confidence(float(weighted)) if weighted is not None else 0.5
    if not valid:
        intent_conf = min(intent_conf, 0.3)

    overall = round(min(company_conf, intent_conf), 3)
    need_review = bool(
        overall < REVIEW_THRESHOLD
        or company_conf < REVIEW_THRESHOLD
        or not valid
    )
    return overall, need_review


def main():
    n = 0
    for lead in db.list_leads(need_review_only=False):
        if lead["status"] == "corrected":
            continue  # 人工已修正的线索不再改动
        result = lead["result"]
        overall, need_review = rescore(result)
        result["confidence_score"] = overall
        result["need_human_review"] = need_review
        db.rescore_lead(lead["id"], result, overall, need_review)
        n += 1
    print(f"已重算 {n} 条待处理线索（corrected 状态跳过）")


if __name__ == "__main__":
    main()
