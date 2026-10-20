"""SQLite 存储：线索入库 + 人工审核反馈闭环。"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "leads.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """建表（幂等）。"""
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transcript TEXT,
            result TEXT,
            confidence REAL,
            need_review INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            field TEXT,
            old_value TEXT,
            new_value TEXT,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conn.commit()
    conn.close()


def insert_lead(transcript, result):
    """插入一条线索，返回 lead_id。"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO leads (transcript, result, confidence, need_review) VALUES (?, ?, ?, ?)",
        (
            transcript,
            json.dumps(result, ensure_ascii=False),
            result.get("confidence_score"),
            1 if result.get("need_human_review") else 0,
        ),
    )
    conn.commit()
    lead_id = cur.lastrowid
    conn.close()
    return lead_id


def update_lead(lead_id, result, status="corrected"):
    """审核后更新线索结果与状态。"""
    conn = get_conn()
    conn.execute(
        "UPDATE leads SET result = ?, confidence = ?, need_review = 0, status = ? WHERE id = ?",
        (
            json.dumps(result, ensure_ascii=False),
            result.get("confidence_score"),
            status,
            lead_id,
        ),
    )
    conn.commit()
    conn.close()


def rescore_lead(lead_id, result, confidence, need_review):
    """重算线索置信度/复核标记（保留 status，不强制清空 need_review）。

    用于评分公式升级后，把旧线索按新公式重算，而无需重新调用 LLM。
    """
    conn = get_conn()
    conn.execute(
        "UPDATE leads SET result = ?, confidence = ?, need_review = ? WHERE id = ?",
        (json.dumps(result, ensure_ascii=False), confidence, 1 if need_review else 0, lead_id),
    )
    conn.commit()
    conn.close()


def save_corrections(lead_id, changes):
    """记录字段修正（反馈闭环样本），changes: [(field, old, new), ...]。"""
    if not changes:
        return
    conn = get_conn()
    for field, old, new in changes:
        conn.execute(
            "INSERT INTO corrections (lead_id, field, old_value, new_value) VALUES (?, ?, ?, ?)",
            (lead_id, field, str(old), str(new)),
        )
    conn.commit()
    conn.close()


def list_leads(need_review_only=True, status="pending"):
    """列出线索，need_review_only=True 时只返回待复核的低置信度线索。"""
    conn = get_conn()
    if need_review_only:
        rows = conn.execute(
            "SELECT * FROM leads WHERE need_review = 1 AND status = ? ORDER BY id DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["result"] = json.loads(d["result"])
        out.append(d)
    return out


def get_lead(lead_id):
    conn = get_conn()
    r = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    if r is None:
        return None
    d = dict(r)
    d["result"] = json.loads(d["result"])
    return d


def count_pending_review():
    """待复核低置信度线索数量（用于导航角标）。"""
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE need_review = 1 AND status = 'pending'"
    ).fetchone()[0]
    conn.close()
    return n


def list_corrections(limit=200):
    """列出人工修正反馈样本（字段、旧值、新值）。"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM corrections ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
