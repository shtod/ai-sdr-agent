"""命令行 Demo：跑通 Agent，输出结构化 JSON。

用法：
    python run_demo.py                     # 使用自带示例
    python run_demo.py path/to/call.txt    # 使用指定通话记录文本
"""
import json
import sys
from pathlib import Path

from src.agent import run

# 强制 UTF-8 输出，避免 Windows 控制台中文乱码
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_SAMPLE = Path(__file__).resolve().parent / "data" / "samples" / "sample_call.txt"


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = DEFAULT_SAMPLE

    text = path.read_text(encoding="utf-8")

    print("=" * 60)
    print("输入通话记录：")
    print("-" * 60)
    print(text)
    print("=" * 60)

    result = run(text)

    print("Agent 输出（结构化 SQL 线索）：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
