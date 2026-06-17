import sqlite3
import os
from datetime import datetime

from config import DB_PATH, DATA_DIR


def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT UNIQUE,
            title TEXT,
            company_name TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            salary_text TEXT,
            location TEXT,
            prefecture TEXT,
            job_category TEXT,
            description_summary TEXT,
            scraped_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pref ON jobs(prefecture)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_company ON jobs(company_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON jobs(job_category)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_details (
            job_id INTEGER PRIMARY KEY REFERENCES jobs(id),
            required_skills TEXT,
            preferred_skills TEXT,
            experience_years TEXT,
            employment_type TEXT,
            industry TEXT,
            work_style TEXT,
            description TEXT,
            benefits TEXT,
            fetched_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS crawl_progress (
            prefecture TEXT,
            page INTEGER,
            status TEXT,
            updated_at TEXT,
            PRIMARY KEY (prefecture, page)
        )
    """)
    conn.commit()
    conn.close()


def bulk_insert_jobs(jobs: list[dict]):
    if not jobs:
        return 0
    conn = get_connection()
    now = datetime.now().isoformat()
    inserted = 0
    for job in jobs:
        job.setdefault("scraped_at", now)
        try:
            conn.execute(
                """INSERT OR IGNORE INTO jobs
                   (source_url, title, company_name, salary_min, salary_max,
                    salary_text, location, prefecture, job_category,
                    description_summary, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job.get("source_url"),
                    job.get("title"),
                    job.get("company_name"),
                    job.get("salary_min"),
                    job.get("salary_max"),
                    job.get("salary_text"),
                    job.get("location"),
                    job.get("prefecture"),
                    job.get("job_category"),
                    job.get("description_summary"),
                    job["scraped_at"],
                ),
            )
            inserted += conn.total_changes
        except sqlite3.Error:
            pass
    conn.commit()
    conn.close()
    return inserted


def bulk_insert_details(details: list[dict]):
    if not details:
        return
    conn = get_connection()
    now = datetime.now().isoformat()
    for d in details:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO job_details
                   (job_id, required_skills, preferred_skills, experience_years,
                    employment_type, industry, work_style, description, benefits, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    d.get("job_id"),
                    d.get("required_skills"),
                    d.get("preferred_skills"),
                    d.get("experience_years"),
                    d.get("employment_type"),
                    d.get("industry"),
                    d.get("work_style"),
                    d.get("description"),
                    d.get("benefits"),
                    now,
                ),
            )
        except sqlite3.Error:
            pass
    conn.commit()
    conn.close()


def mark_page_done(prefecture: str, page: int):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO crawl_progress (prefecture, page, status, updated_at)
           VALUES (?, ?, 'done', ?)""",
        (prefecture, page, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def is_page_done(prefecture: str, page: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT status FROM crawl_progress WHERE prefecture=? AND page=?",
        (prefecture, page),
    ).fetchone()
    conn.close()
    return row is not None and row["status"] == "done"


def get_job_count(prefecture: str | None = None) -> int:
    conn = get_connection()
    if prefecture:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM jobs WHERE prefecture=?", (prefecture,)
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()
    conn.close()
    return row["c"]


def search_jobs(keyword: str = "", prefecture: str = "",
                salary_min: int | None = None) -> list[dict]:
    conn = get_connection()
    conditions = []
    params = []
    if keyword:
        conditions.append(
            "(title LIKE ? OR description_summary LIKE ? OR job_category LIKE ?)"
        )
        params.extend([f"%{keyword}%"] * 3)
    if prefecture:
        conditions.append("prefecture = ?")
        params.append(prefecture)
    if salary_min:
        conditions.append("salary_max >= ?")
        params.append(salary_min)
    where = " AND ".join(conditions) if conditions else "1=1"
    rows = conn.execute(
        f"SELECT * FROM jobs WHERE {where} ORDER BY salary_max DESC", params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_jobs_without_details(keyword: str = "", prefecture: str = "",
                              limit: int = 1000) -> list[dict]:
    conn = get_connection()
    conditions = ["d.job_id IS NULL"]
    params = []
    if keyword:
        conditions.append(
            "(j.title LIKE ? OR j.description_summary LIKE ?)"
        )
        params.extend([f"%{keyword}%"] * 2)
    if prefecture:
        conditions.append("j.prefecture = ?")
        params.append(prefecture)
    where = " AND ".join(conditions)
    rows = conn.execute(
        f"""SELECT j.* FROM jobs j
            LEFT JOIN job_details d ON j.id = d.job_id
            WHERE {where} LIMIT ?""",
        params + [limit],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_jobs_with_details(keyword: str = "", prefecture: str = "") -> list[dict]:
    conn = get_connection()
    conditions = ["d.job_id IS NOT NULL"]
    params = []
    if keyword:
        conditions.append(
            "(j.title LIKE ? OR d.required_skills LIKE ? OR d.description LIKE ?)"
        )
        params.extend([f"%{keyword}%"] * 3)
    if prefecture:
        conditions.append("j.prefecture = ?")
        params.append(prefecture)
    where = " AND ".join(conditions)
    rows = conn.execute(
        f"""SELECT j.*, d.required_skills, d.preferred_skills, d.experience_years,
                   d.employment_type, d.industry, d.work_style, d.benefits
            FROM jobs j
            JOIN job_details d ON j.id = d.job_id
            WHERE {where}""",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
