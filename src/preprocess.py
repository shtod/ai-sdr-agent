"""预处理：话轮切分、基础正则实体抽取。"""
import re

# 常见说话人前缀
SPEAKER_RE = re.compile(
    r"^\s*(销售|客户|SDR|客服|坐席|客户经理|销售顾问|业务员|BD)\s*[：:]\s*(.*)$"
)

# 手机号：真实 11 位或掩码形式（如 138xxxx1234）
PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9}|1[3-9][\dxX*]{8}\d)(?!\d)")


def split_turns(text):
    """按说话人切分话轮，返回 [(speaker, content), ...]。

    无法识别说话人的行归为 "unknown"，保留原文。
    """
    turns = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = SPEAKER_RE.match(line)
        if m:
            turns.append((m.group(1), m.group(2).strip()))
        else:
            turns.append(("unknown", line))
    return turns


def extract_phone(text):
    """正则兜底提取手机号（含掩码形式），未命中返回 None。"""
    m = PHONE_RE.search(text)
    return m.group(1) if m else None
