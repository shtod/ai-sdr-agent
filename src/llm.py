"""DeepSeek LLM 客户端封装（OpenAI 兼容接口）。

统一提供两个能力：
- chat(): 返回原始文本，网络/服务异常时自动重试
- chat_json(): 以 JSON 模式调用并稳健解析为 dict；任何失败返回 None（调用方降级处理）
"""
import json
import re
import time

from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


def chat(messages, temperature=0.0, max_tokens=3000, json_mode=False, retries=2):
    """调用 DeepSeek，返回模型输出文本；异常时退避重试，重试耗尽则抛出。"""
    client = get_client()
    kwargs = dict(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001 网络抖动/限流等，重试
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_err


def _extract_json(text):
    """从模型返回文本中稳健地解析 JSON 对象。"""
    if not text:
        return None
    text = text.strip()
    # 去掉 ```json ... ``` 代码块
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 截取首个 { 到最后一个 } 之间的内容
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def chat_json(messages, temperature=0.0, max_tokens=3000):
    """JSON 模式调用并解析；失败时回退为普通调用再解析，最终仍失败返回 None。"""
    try:
        content = chat(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)
    except Exception:
        content = None
    data = _extract_json(content) if content else None
    if data is not None:
        return data
    # 回退：不强制 json_mode，从自由文本里提取 JSON
    try:
        content = chat(messages, temperature=temperature, max_tokens=max_tokens, json_mode=False)
    except Exception:
        return None
    return _extract_json(content)
