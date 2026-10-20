"""人工干预管理工具（Flask，多页面 + 顶部导航）。

用法：
    python app.py          # 启动后浏览器打开 http://127.0.0.1:5000

页面：
- /            概览（统计 + 快捷操作）
- /add         录入新通话记录，运行 Agent 入库
- /leads       全部线索
- /review      低置信度待复核队列（修正企业抬头/意向等级，反馈闭环）
- /feedback    反馈样本（修正记录）
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, flash, redirect, render_template, request, session, url_for

import db
from src import schema
from src.agent import run

app = Flask(__name__)
app.secret_key = "ai-sdr-demo-secret"

db.init_db()

INTENT_OPTIONS = ["high", "medium", "low"]
EDITABLE_FIELDS = ["company_name", "intent_level", "demand_summary"]


@app.context_processor
def inject_globals():
    """向所有模板注入导航角标计数。"""
    return {"pending_count": db.count_pending_review()}


def _other_fields(result):
    """其余字段只读展示。"""
    keys = [k for k in schema.SQL_FIELDS if k not in EDITABLE_FIELDS]
    return json.dumps({k: result.get(k) for k in keys}, ensure_ascii=False)


def _stats():
    leads = db.list_leads(need_review_only=False)
    dist = {"high": 0, "medium": 0, "low": 0}
    for lead in leads:
        lv = lead["result"].get("intent_level")
        if lv in dist:
            dist[lv] += 1
    return {
        "total": len(leads),
        "pending": sum(1 for l in leads if l["need_review"] and l["status"] == "pending"),
        "corrected": sum(1 for l in leads if l["status"] == "corrected"),
        "dist": dist,
    }


@app.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard", stats=_stats())


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        transcript = (request.form.get("transcript") or "").strip()
        if transcript:
            result = run(transcript)
            db.insert_lead(transcript, result)
            session["last_transcript"] = transcript
            session["last_result"] = result
            flash(
                f"已入库：置信度 {result['confidence_score']}，"
                f"需复核={'是' if result['need_human_review'] else '否'}"
            )
        else:
            flash("请输入通话记录")
        # 重定向回本页（PRG），在录入页直接展示 Agent 输出
        return redirect(url_for("add"))

    last_transcript = session.pop("last_transcript", None)
    last_result = session.pop("last_result", None)
    last_json = (
        json.dumps(last_result, ensure_ascii=False, indent=2) if last_result else None
    )
    return render_template(
        "add.html",
        active="add",
        last_transcript=last_transcript,
        last_result=last_result,
        last_json=last_json,
    )


@app.route("/leads")
def leads():
    return render_template("leads.html", active="leads", leads=db.list_leads(need_review_only=False))


@app.route("/review", methods=["GET", "POST"])
def review():
    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "save":
            lead_id = int(request.form.get("lead_id", 0))
            lead = db.get_lead(lead_id)
            if lead is None:
                flash(f"线索 {lead_id} 不存在")
                return redirect(url_for("review"))
            result = lead["result"]
            changes = []
            for field in EDITABLE_FIELDS:
                new = (request.form.get(field) or "").strip()
                old = result.get(field) or ""
                if new != old:
                    changes.append((field, old or None, new or None))
                    result[field] = new or None
            result["need_human_review"] = False
            db.update_lead(lead_id, result, status="corrected")
            db.save_corrections(lead_id, changes)
            flash(f"线索 {lead_id} 已保存修正，记录 {len(changes)} 条反馈样本")

        if action == "batch":
            ids = [int(x) for x in request.form.getlist("lead_ids")]
            intent = request.form.get("intent_level", "low")
            n = 0
            for lead_id in ids:
                lead = db.get_lead(lead_id)
                if lead is None:
                    continue
                result = lead["result"]
                old = result.get("intent_level")
                if old != intent:
                    db.save_corrections(lead_id, [("intent_level", old, intent)])
                result["intent_level"] = intent
                result["need_human_review"] = False
                db.update_lead(lead_id, result, status="corrected")
                n += 1
            flash(f"已批量处理 {n} 条线索")

        return redirect(url_for("review"))

    leads = db.list_leads(need_review_only=True)
    for lead in leads:
        lead["others"] = _other_fields(lead["result"])
    return render_template(
        "review.html", active="review", leads=leads, intent_options=INTENT_OPTIONS
    )


@app.route("/feedback")
def feedback():
    return render_template("feedback.html", active="feedback", corrections=db.list_corrections())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
