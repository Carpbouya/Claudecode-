import sqlite3
import os
from datetime import datetime

from config import DB_PATH, DATA_DIR


def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT UNIQUE,
            title TEXT,
            company_name TEXT,
            industry TEXT,
            job_category TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            salary_text TEXT,
            location TEXT,
            prefecture TEXT,
            work_style TEXT,
            required_skills TEXT,
            preferred_skills TEXT,
            experience_years TEXT,
            employment_type TEXT,
            description TEXT,
            benefits TEXT,
            scraped_at TEXT,
            updated_at TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_prefecture ON jobs(prefecture)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(job_category)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name)
    """)
    conn.commit()
    conn.close()


def upsert_job(job_data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    job_data["updated_at"] = now
    if "scraped_at" not in job_data:
        job_data["scraped_at"] = now

    columns = ", ".join(job_data.keys())
    placeholders = ", ".join(["?"] * len(job_data))
    update_clause = ", ".join(
        [f"{k} = excluded.{k}" for k in job_data.keys() if k != "source_url"]
    )

    sql = f"""
        INSERT INTO jobs ({columns}) VALUES ({placeholders})
        ON CONFLICT(source_url) DO UPDATE SET {update_clause}
    """
    cursor.execute(sql, list(job_data.values()))
    conn.commit()
    conn.close()


def bulk_upsert_jobs(jobs: list[dict]):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    for job_data in jobs:
        job_data["updated_at"] = now
        if "scraped_at" not in job_data:
            job_data["scraped_at"] = now

        columns = ", ".join(job_data.keys())
        placeholders = ", ".join(["?"] * len(job_data))
        update_clause = ", ".join(
            [f"{k} = excluded.{k}" for k in job_data.keys() if k != "source_url"]
        )

        sql = f"""
            INSERT INTO jobs ({columns}) VALUES ({placeholders})
            ON CONFLICT(source_url) DO UPDATE SET {update_clause}
        """
        cursor.execute(sql, list(job_data.values()))

    conn.commit()
    conn.close()


def get_all_jobs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY scraped_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_job_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM jobs")
    result = cursor.fetchone()
    conn.close()
    return result["count"]


def search_jobs(keyword=None, prefecture=None, category=None,
                salary_min=None, salary_max=None):
    conn = get_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if keyword:
        conditions.append("(title LIKE ? OR description LIKE ? OR required_skills LIKE ?)")
        params.extend([f"%{keyword}%"] * 3)
    if prefecture:
        conditions.append("prefecture = ?")
        params.append(prefecture)
    if category:
        conditions.append("job_category = ?")
        params.append(category)
    if salary_min:
        conditions.append("salary_max >= ?")
        params.append(salary_min)
    if salary_max:
        conditions.append("salary_min <= ?")
        params.append(salary_max)

    where = " AND ".join(conditions) if conditions else "1=1"
    cursor.execute(f"SELECT * FROM jobs WHERE {where} ORDER BY scraped_at DESC", params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
