"""确定性逻辑单元测试。

覆盖作业两大难点的可验证部分：
- 企业抬头识别：词库精确 / 同音错字 / 字符级错字匹配，以及「无误召回」；
- 意向度识别：评分卡加权后的等级映射；
- 结构化输出：字段规范化、手机号正则兜底。

运行方式：
    python -m pytest tests/ -v        # 推荐
    python tests/test_core.py         # 无 pytest 环境亦可直接跑
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import INTENT_HIGH_THRESHOLD  # noqa: E402
from src import company_resolution, preprocess, schema  # noqa: E402
from src.intent_scoring import _clamp_score, _confidence, _level  # noqa: E402

LEXICON = [
    {"alias": "木里木外", "full_name": "木里木外家居"},
    {"alias": "欧派", "full_name": "欧派家居"},
    {"alias": "索菲亚", "full_name": "索菲亚家居"},
    {"alias": "金牌", "full_name": "金牌厨柜"},
    {"alias": "我乐", "full_name": "我乐家居"},
    {"alias": "玛格", "full_name": "玛格家居"},
]

HAS_PYPINYIN = company_resolution._pinyin("派") is not None


def _hits(text):
    return {h["alias"] for h in company_resolution.match_lexicon(text, LEXICON)}


def test_exact_alias_match():
    assert "木里木外" in _hits("我们公司叫木里木外，做全屋定制")


def test_char_typo_match_three_chars():
    # 索非亚 -> 索菲亚（3 字错一字，编辑距离 1）
    assert "索菲亚" in _hits("我们公司是索非亚")


def test_homophone_typo_match_two_chars():
    if not HAS_PYPINYIN:
        return  # 无 pypinyin 环境跳过
    # 欧排 -> 欧派（2 字同音错字，靠拼音匹配）
    assert "欧派" in _hits("我们一直用的是欧排")


def test_no_false_positive_common_words():
    # 「我们/价格/品牌」不得误命中「我乐/玛格/金牌」
    hits = _hits("我们做家具的，你先说下价格，别的品牌以后再说")
    assert "我乐" not in hits
    assert "玛格" not in hits
    assert "金牌" not in hits


def test_phone_extraction():
    assert preprocess.extract_phone("手机号138xxxx1234给我") == "138xxxx1234"
    assert preprocess.extract_phone("电话是13812341234") == "13812341234"
    assert preprocess.extract_phone("这里没有电话") is None


def test_schema_normalize_types():
    r = schema.normalize(
        {
            "intent_level": "HIGH",
            "confidence_score": "0.75",
            "need_human_review": "true",
            "industry": "   ",
        }
    )
    assert r["intent_level"] == "high"
    assert r["confidence_score"] == 0.75
    assert r["need_human_review"] is True
    assert r["industry"] is None


def test_schema_numeric_mendian_shejishi():
    r = schema.normalize({"mendian": "5家", "shejishi": "30人"})
    assert r["mendian"] == 5
    assert r["shejishi"] == 30


def test_intent_level_mapping():
    assert _level(2.0) == "high"
    assert _level(INTENT_HIGH_THRESHOLD) == "high"
    assert _level(1.2) == "medium"
    assert _level(0.3) == "low"


def test_clamp_score():
    assert _clamp_score("2") == 2.0
    assert _clamp_score(5) == 2.0
    assert _clamp_score(-1) == 0.0
    assert _clamp_score("x") == 0.0


def test_intent_confidence_margin():
    # 远离分界线（含两端极值）→ 高置信
    assert _confidence(2.0) == 1.0
    assert _confidence(0.0) == 1.0
    # 恰好落在分界线上 → 低置信
    assert _confidence(INTENT_HIGH_THRESHOLD) <= 0.6
    assert _confidence(0.9) <= 0.6
    # 中意向区间中部比贴近 high 分界线更确定（旧公式会颠倒这个关系）
    assert _confidence(1.2) > _confidence(1.4)


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {name}: {e!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
