# AI SDR Agent

输入销售电话沟通记录文本，自动输出结构化 SQL（Sales Qualified Lead）线索，并配套低置信度线索的人工干预管理工具。

## 目录结构

```
ai-sdr-agent/
├── config.py                  # 全局配置（API、评分卡阈值）
├── run_demo.py                # 命令行 Demo：跑通 Agent
├── app.py                     # Flask 人工干预工具（多页面）
├── db.py                      # SQLite 存储 + 反馈闭环
├── rescore_leads.py           # 评分公式升级后的数据迁移脚本
├── requirements.txt
├── .env.example               # 配置模板（真实配置填 .env）
├── src/
│   ├── agent.py               # 主流水线编排
│   ├── llm.py                 # DeepSeek LLM 封装（OpenAI 兼容）
│   ├── schema.py              # SQL 字段定义与规范化
│   ├── prompts.py             # Prompt 模板
│   ├── preprocess.py          # 话轮切分、正则兜底
│   ├── intent_recognition.py  # 意图识别（有效线索 + 类型）
│   ├── extract.py             # 信息抽取
│   ├── company_resolution.py  # 企业抬头还原（难点1）
│   └── intent_scoring.py      # 意向评分卡（难点2）
├── data/
│   ├── samples/               # 测试样本（高意向/错字/低意向）
│   └── lexicon/company_lexicon.json
├── templates/                 # Flask 页面模板
├── tests/test_core.py         # 确定性逻辑单元测试
└── docs/design.md             # 设计文档
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置密钥：复制 .env.example 为 .env，填入 DEEPSEEK_API_KEY

# 3. 命令行跑通示例
python run_demo.py

# 4. 启动人工干预工具（浏览器打开 http://127.0.0.1:5000）
python app.py
```

## Agent 输出字段

| 字段 | 说明 |
|---|---|
| company_name | 企业抬头（还原后的全称） |
| industry / area | 行业 / 地区 |
| contact_name / contact_title / phone | 联系人 / 职位 / 手机号 |
| intent_level | 意向等级 high / medium / low |
| intent_reason | 意向判断依据（逐维度） |
| demand_summary | 客户需求摘要 |
| mendian / shejishi | 门店数 / 设计师人数 |
| call_time / next_action | 通话时间 / 建议下一步 |
| confidence_score | 整体置信度 0.0~1.0 |
| need_human_review | 是否需要人工复核 |

## 两大难点方案（简述）

- **企业抬头识别**：候选提取 + 本地行业词库三层匹配（精确 / 长度门控编辑距离 / 拼音同音） + 大模型结合上下文/行业知识还原全称，输出全称、别名、依据与置信度。
- **客户意向度识别**：评分卡（预算/时间/人数/痛点/主动询问/决策角色 6 维加权）→ high/medium/low + 依据。

详见 `docs/design.md`。

## 测试与验证

```bash
# 单元测试（确定性逻辑：词库匹配/手机号/字段规范化/意向分级映射）
python -m pytest tests/ -v
# 或不用 pytest 直接跑
python tests/test_core.py

# 命令行跑通三个示例场景
python run_demo.py                                    # 高意向 + 简称「木里木外」
python run_demo.py data/samples/sample_typo_company.txt   # 转写错字「索非亚」→ 索菲亚家居
python run_demo.py data/samples/sample_low_intent.txt     # 低意向「随便问问」
```
