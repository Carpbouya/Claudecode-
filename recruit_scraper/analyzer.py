"""
求人データ分析モジュール

収集した求人データから以下の分析を行う:
- 給与水準の市場調査（職種別・地域別）
- 求められるスキルの頻度分析
- 競合他社の採用動向
- 雇用形態・勤務地の傾向分析
"""

import re
from collections import Counter

import pandas as pd

from models import get_connection


def load_dataframe() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM jobs", conn)
    conn.close()
    return df


def salary_analysis(df: pd.DataFrame) -> dict:
    salary_df = df.dropna(subset=["salary_min", "salary_max"])
    if salary_df.empty:
        return {"error": "給与データがありません"}

    salary_df = salary_df.copy()
    salary_df["salary_avg"] = (salary_df["salary_min"] + salary_df["salary_max"]) / 2

    overall = {
        "平均年収": int(salary_df["salary_avg"].mean()),
        "中央値年収": int(salary_df["salary_avg"].median()),
        "最低年収": int(salary_df["salary_min"].min()),
        "最高年収": int(salary_df["salary_max"].max()),
        "データ件数": len(salary_df),
    }

    by_prefecture = {}
    if "prefecture" in salary_df.columns:
        for pref, group in salary_df.groupby("prefecture"):
            if not pref:
                continue
            by_prefecture[pref] = {
                "平均年収": int(group["salary_avg"].mean()),
                "中央値年収": int(group["salary_avg"].median()),
                "件数": len(group),
            }

    by_category = {}
    if "job_category" in salary_df.columns:
        for cat, group in salary_df.groupby("job_category"):
            if not cat:
                continue
            by_category[cat] = {
                "平均年収": int(group["salary_avg"].mean()),
                "中央値年収": int(group["salary_avg"].median()),
                "件数": len(group),
            }

    return {
        "全体": overall,
        "都道府県別": by_prefecture,
        "職種別": by_category,
    }


def skill_analysis(df: pd.DataFrame) -> dict:
    all_skills_text = " ".join(
        df["required_skills"].dropna().astype(str).tolist()
        + df["preferred_skills"].dropna().astype(str).tolist()
    )

    tech_keywords = [
        "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C#", "C++",
        "PHP", "Ruby", "Swift", "Kotlin", "Scala", "R言語",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Linux",
        "React", "Vue", "Angular", "Next.js", "Node.js",
        "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Oracle",
        "Git", "CI/CD", "Terraform", "Ansible",
        "機械学習", "AI", "深層学習", "データ分析", "統計",
        "プロジェクトマネジメント", "アジャイル", "スクラム",
        "TOEIC", "英語", "中国語",
        "簿記", "会計", "税務",
        "マネジメント", "リーダー", "マネージャー",
    ]

    keyword_counts = Counter()
    for keyword in tech_keywords:
        count = len(re.findall(re.escape(keyword), all_skills_text, re.IGNORECASE))
        if count > 0:
            keyword_counts[keyword] = count

    by_category = {}
    for cat, group in df.groupby("job_category"):
        if not cat:
            continue
        cat_text = " ".join(
            group["required_skills"].dropna().astype(str).tolist()
            + group["preferred_skills"].dropna().astype(str).tolist()
        )
        cat_counts = Counter()
        for keyword in tech_keywords:
            count = len(re.findall(re.escape(keyword), cat_text, re.IGNORECASE))
            if count > 0:
                cat_counts[keyword] = count
        if cat_counts:
            by_category[cat] = dict(cat_counts.most_common(15))

    return {
        "全体スキル頻度": dict(keyword_counts.most_common(30)),
        "職種別スキル": by_category,
    }


def company_analysis(df: pd.DataFrame) -> dict:
    company_counts = df["company_name"].value_counts()
    top_hiring = company_counts.head(30).to_dict()

    company_salary = {}
    salary_df = df.dropna(subset=["salary_min", "salary_max"]).copy()
    salary_df["salary_avg"] = (salary_df["salary_min"] + salary_df["salary_max"]) / 2

    for company, group in salary_df.groupby("company_name"):
        if not company or len(group) < 2:
            continue
        company_salary[company] = {
            "平均年収": int(group["salary_avg"].mean()),
            "求人数": len(group),
        }

    sorted_by_salary = dict(
        sorted(company_salary.items(), key=lambda x: x[1]["平均年収"], reverse=True)[:20]
    )

    industry_counts = df["industry"].value_counts().head(20).to_dict()

    return {
        "採用数上位企業": top_hiring,
        "年収上位企業": sorted_by_salary,
        "業種別求人数": {k: v for k, v in industry_counts.items() if k},
    }


def location_analysis(df: pd.DataFrame) -> dict:
    pref_counts = df["prefecture"].value_counts().to_dict()
    pref_counts = {k: v for k, v in pref_counts.items() if k}

    work_style_counts = df["work_style"].value_counts().to_dict()
    work_style_counts = {k: v for k, v in work_style_counts.items() if k}

    remote_keywords = ["リモート", "在宅", "テレワーク", "フルリモート"]
    remote_count = 0
    for _, row in df.iterrows():
        text = f"{row.get('work_style', '')} {row.get('description', '')} {row.get('title', '')}"
        if any(kw in str(text) for kw in remote_keywords):
            remote_count += 1

    return {
        "都道府県別求人数": pref_counts,
        "勤務形態": work_style_counts,
        "リモートワーク求人数": remote_count,
        "リモートワーク比率": f"{remote_count / len(df) * 100:.1f}%" if len(df) > 0 else "0%",
    }


def employment_type_analysis(df: pd.DataFrame) -> dict:
    type_counts = df["employment_type"].value_counts().to_dict()
    type_counts = {k: v for k, v in type_counts.items() if k}
    return {"雇用形態別": type_counts}


def generate_full_report(df: pd.DataFrame) -> dict:
    report = {
        "概要": {
            "総求人数": len(df),
            "企業数": df["company_name"].nunique(),
            "都道府県数": df["prefecture"].nunique(),
            "職種カテゴリ数": df["job_category"].nunique(),
        },
        "給与分析": salary_analysis(df),
        "スキル分析": skill_analysis(df),
        "企業分析": company_analysis(df),
        "地域分析": location_analysis(df),
        "雇用形態分析": employment_type_analysis(df),
    }
    return report


def export_csv(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False, encoding="utf-8-sig")
