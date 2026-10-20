"""Prompt 模板集中管理，便于调优与讲解。

模板中的 `{system}`、`{text}`、`{lexicon}` 为占位符，用 render() 替换；
JSON 示例里的 `{` `}` 保持原样（render 不做 format 解析，避免转义问题）。
"""


def render(template, **values):
    """把模板里的 {key} 占位符替换为对应值（不解析 JSON 大括号）。"""
    s = template
    for k, v in values.items():
        s = s.replace("{" + k + "}", str(v))
    return s


SYSTEM_BASE = (
    "你是酷家乐 XDR 团队的 AI SDR Agent，负责把销售电话沟通记录（可能含口语、简称、"
    "转写错误）自动解析为结构化 SQL（Sales Qualified Lead）线索。"
    "你只输出 JSON，不输出任何多余解释。字段缺失时填 null，不要编造。"
)

# 第一步：结构化信息抽取
EXTRACT_PROMPT = (
    "{system}\n\n"
    "请从下面的电话沟通记录中抽取以下信息，输出 JSON：\n"
    "{\n"
    '  "industry": "行业（如全屋定制/高定/家具等，若未明确则 null）",\n'
    '  "area": "地区（如杭州，若未提及则 null）",\n'
    '  "contact_name": "联系人称呼（如张总）",\n'
    '  "contact_title": "职位（如总经理/负责人；称呼为「X总」时可填「负责人/总经理」，若未明确则 null）",\n'
    '  "phone": "手机号（含掩码形式，如 138xxxx1234）",\n'
    '  "mendian": "门店数（数字或描述，未提及则 null）",\n'
    '  "shejishi": "设计师人数（数字或描述，未提及则 null）",\n'
    '  "demand_summary": "客户需求/痛点一句话总结",\n'
    '  "call_time": "通话时间（若记录中有则给出，否则 null）",\n'
    '  "next_action": "建议下一步动作"\n'
    "}\n\n"
    "沟通记录：\n{text}"
)

# 第三步：企业抬头识别与还原（难点 1）
COMPANY_PROMPT = (
    "{system}\n\n"
    "任务：还原客户企业的全称（企业抬头）。客户口语中可能出现简称、别称、品牌名，"
    "甚至转写错误（如把品牌名写错字），请结合上下文、行业知识还原最可能的全称。\n\n"
    "本地行业词库命中的候选如下（可能为空）：\n{lexicon}\n\n"
    "要求输出 JSON：\n"
    "{\n"
    '  "company_name": "还原后的企业全称",\n'
    '  "alias": "对话中客户实际说到的名称",\n'
    '  "confidence": 0.0~1.0 还原置信度,\n'
    '  "reason": "还原依据（结合了哪些上下文/行业知识）"\n'
    "}\n\n"
    "沟通记录：\n{text}"
)

# 第四步：客户意向度评分（难点 2）——先给每个维度打分，代码再加权
INTENT_PROMPT = (
    "{system}\n\n"
    "任务：对客户意向进行评分卡打分。请针对以下 6 个维度分别打分（0/1/2 分），"
    "并给出简短依据。0=无信号，1=弱信号，2=强信号。\n"
    "- budget 预算：是否提及预算或价格接受度\n"
    "- timeline 时间紧迫度：是否有明确上线/试用的时间计划\n"
    "- scale 规模/人数：是否提及门店数、设计师人数等规模\n"
    "- painpoint 痛点明确度：是否描述了具体业务痛点\n"
    "- proactiveness 主动询问：是否主动追问方案、价格、演示等\n"
    "- decision_role 决策角色：联系人是否为决策人（如总/负责人）\n\n"
    "要求输出 JSON：\n"
    "{\n"
    '  "scores": {"budget": 0, "timeline": 0, "scale": 0, "painpoint": 0, '
    '"proactiveness": 0, "decision_role": 0},\n'
    '  "evidence": {"budget": "依据", "timeline": "依据", "scale": "依据", '
    '"painpoint": "依据", "proactiveness": "依据", "decision_role": "依据"}\n'
    "}\n\n"
    "沟通记录：\n{text}"
)

# 第零步：意图识别——判断是否为有效销售线索 + 对话类型
INTENT_RECOGNITION_PROMPT = (
    "{system}\n\n"
    "任务：判断这段电话沟通是否为有效的销售线索对话，并给出对话类型。\n"
    "对话类型候选：需求咨询 / 价格咨询 / 竞品对比 / 随便问问 / 售后投诉 / 无效通话\n\n"
    "要求输出 JSON：\n"
    "{\n"
    '  "is_valid_lead": true 或 false（是否值得录入 CRM 的销售线索）,\n'
    '  "conversation_type": "对话类型",\n'
    '  "reason": "判断依据（一两句话）"\n'
    "}\n\n"
    "沟通记录：\n{text}"
)
