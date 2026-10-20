"""全局配置：从 .env 读取 DeepSeek API 配置与评分阈值。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

# 置信度阈值：低于该值标记 need_human_review=True
REVIEW_THRESHOLD = float(os.getenv("REVIEW_THRESHOLD", "0.7"))

# 意向评分卡：维度 -> 权重（合计 1.0）
INTENT_DIMENSIONS = [
    {"key": "budget", "label": "预算", "weight": 0.25},
    {"key": "timeline", "label": "时间紧迫度", "weight": 0.25},
    {"key": "scale", "label": "规模/人数", "weight": 0.10},
    {"key": "painpoint", "label": "痛点明确度", "weight": 0.15},
    {"key": "proactiveness", "label": "主动询问", "weight": 0.15},
    {"key": "decision_role", "label": "决策角色", "weight": 0.10},
]

# 评分卡加权总分（0~2 区间）映射到意向等级
INTENT_HIGH_THRESHOLD = 1.5
INTENT_MEDIUM_THRESHOLD = 0.9
