"""
求人市場分析ダッシュボード

Flask + Plotly によるインタラクティブダッシュボード。
スクレイピングで収集した求人データを可視化する。
"""

import json

import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from flask import Flask, render_template, request, jsonify

from config import DASHBOARD_HOST, DASHBOARD_PORT, PREFECTURES, JOB_CATEGORIES
from models import init_db, get_connection
from analyzer import (
    load_dataframe,
    salary_analysis,
    skill_analysis,
    company_analysis,
    location_analysis,
    generate_full_report,
    export_csv,
)

app = Flask(__name__)


def create_salary_chart(df: pd.DataFrame) -> str:
    salary_df = df.dropna(subset=["salary_min", "salary_max"]).copy()
    if salary_df.empty:
        return "{}"
    salary_df["salary_avg"] = (salary_df["salary_min"] + salary_df["salary_max"]) / 2

    pref_salary = (
        salary_df.groupby("prefecture")["salary_avg"]
        .agg(["mean", "count"])
        .reset_index()
    )
    pref_salary = pref_salary[pref_salary["prefecture"] != ""]
    pref_salary = pref_salary.sort_values("mean", ascending=True)

    fig = px.bar(
        pref_salary,
        x="mean",
        y="prefecture",
        orientation="h",
        title="都道府県別 平均年収",
        labels={"mean": "平均年収（円）", "prefecture": "都道府県"},
        text="count",
        color="mean",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(height=max(400, len(pref_salary) * 30))
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_category_salary_chart(df: pd.DataFrame) -> str:
    salary_df = df.dropna(subset=["salary_min", "salary_max"]).copy()
    if salary_df.empty:
        return "{}"
    salary_df["salary_avg"] = (salary_df["salary_min"] + salary_df["salary_max"]) / 2

    cat_salary = (
        salary_df.groupby("job_category")["salary_avg"]
        .agg(["mean", "median", "count"])
        .reset_index()
    )
    cat_salary = cat_salary[cat_salary["job_category"] != ""]
    cat_salary = cat_salary.sort_values("mean", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=cat_salary["job_category"],
        x=cat_salary["mean"],
        name="平均年収",
        orientation="h",
        marker_color="#636EFA",
    ))
    fig.add_trace(go.Bar(
        y=cat_salary["job_category"],
        x=cat_salary["median"],
        name="中央値年収",
        orientation="h",
        marker_color="#EF553B",
    ))
    fig.update_layout(
        title="職種別 年収比較",
        barmode="group",
        height=max(400, len(cat_salary) * 40),
        xaxis_title="年収（円）",
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_skill_chart(df: pd.DataFrame) -> str:
    result = skill_analysis(df)
    skills = result.get("全体スキル頻度", {})
    if not skills:
        return "{}"

    skill_df = pd.DataFrame(
        list(skills.items()), columns=["スキル", "出現回数"]
    ).sort_values("出現回数", ascending=True).tail(20)

    fig = px.bar(
        skill_df,
        x="出現回数",
        y="スキル",
        orientation="h",
        title="求められるスキル TOP20",
        color="出現回数",
        color_continuous_scale="Bluered",
    )
    fig.update_layout(height=600)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_location_chart(df: pd.DataFrame) -> str:
    pref_counts = df["prefecture"].value_counts().reset_index()
    pref_counts.columns = ["prefecture", "count"]
    pref_counts = pref_counts[pref_counts["prefecture"] != ""]

    fig = px.pie(
        pref_counts.head(15),
        values="count",
        names="prefecture",
        title="地域別 求人分布 TOP15",
    )
    fig.update_layout(height=500)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_company_chart(df: pd.DataFrame) -> str:
    company_counts = df["company_name"].value_counts().head(20).reset_index()
    company_counts.columns = ["company_name", "count"]
    company_counts = company_counts[company_counts["company_name"] != ""]
    company_counts = company_counts.sort_values("count", ascending=True)

    fig = px.bar(
        company_counts,
        x="count",
        y="company_name",
        orientation="h",
        title="採用数 上位企業 TOP20",
        color="count",
        color_continuous_scale="Greens",
    )
    fig.update_layout(height=600)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_salary_distribution_chart(df: pd.DataFrame) -> str:
    salary_df = df.dropna(subset=["salary_min", "salary_max"]).copy()
    if salary_df.empty:
        return "{}"
    salary_df["salary_avg"] = (salary_df["salary_min"] + salary_df["salary_max"]) / 2

    fig = px.histogram(
        salary_df,
        x="salary_avg",
        nbins=30,
        title="年収分布",
        labels={"salary_avg": "年収（円）", "count": "求人数"},
        color_discrete_sequence=["#636EFA"],
    )
    fig.update_layout(height=400)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


@app.route("/")
def index():
    df = load_dataframe()
    report = generate_full_report(df) if not df.empty else {}

    charts = {}
    if not df.empty:
        charts["salary_by_pref"] = create_salary_chart(df)
        charts["salary_by_category"] = create_category_salary_chart(df)
        charts["skills"] = create_skill_chart(df)
        charts["location"] = create_location_chart(df)
        charts["company"] = create_company_chart(df)
        charts["salary_distribution"] = create_salary_distribution_chart(df)

    return render_template(
        "dashboard.html",
        report=report,
        charts=charts,
        total_jobs=len(df),
        prefectures=list(PREFECTURES.keys()),
        categories=list(JOB_CATEGORIES.keys()),
    )


@app.route("/api/search")
def api_search():
    keyword = request.args.get("keyword", "")
    prefecture = request.args.get("prefecture", "")
    category = request.args.get("category", "")
    salary_min = request.args.get("salary_min", type=int)
    salary_max = request.args.get("salary_max", type=int)

    df = load_dataframe()
    if df.empty:
        return jsonify({"jobs": [], "count": 0})

    if keyword:
        mask = (
            df["title"].str.contains(keyword, case=False, na=False)
            | df["description"].str.contains(keyword, case=False, na=False)
            | df["required_skills"].str.contains(keyword, case=False, na=False)
        )
        df = df[mask]
    if prefecture:
        df = df[df["prefecture"] == prefecture]
    if category:
        df = df[df["job_category"].str.contains(category, case=False, na=False)]
    if salary_min:
        df = df[df["salary_max"] >= salary_min]
    if salary_max:
        df = df[df["salary_min"] <= salary_max]

    jobs = df.head(100).to_dict("records")
    return jsonify({"jobs": jobs, "count": len(df)})


@app.route("/api/report")
def api_report():
    df = load_dataframe()
    if df.empty:
        return jsonify({"error": "データがありません"})
    report = generate_full_report(df)
    return jsonify(report)


@app.route("/api/compare")
def api_compare():
    companies = request.args.get("companies", "")
    if not companies:
        return jsonify({"error": "企業名を指定してください"})

    company_list = [c.strip() for c in companies.split(",")]
    df = load_dataframe()
    if df.empty:
        return jsonify({"error": "データがありません"})

    result = {}
    for company in company_list:
        company_df = df[df["company_name"].str.contains(company, case=False, na=False)]
        if company_df.empty:
            continue
        salary_df = company_df.dropna(subset=["salary_min", "salary_max"])
        avg_salary = None
        if not salary_df.empty:
            avg_salary = int(
                ((salary_df["salary_min"] + salary_df["salary_max"]) / 2).mean()
            )
        result[company] = {
            "求人数": len(company_df),
            "平均年収": avg_salary,
            "職種": company_df["job_category"].value_counts().head(5).to_dict(),
            "勤務地": company_df["prefecture"].value_counts().head(5).to_dict(),
        }

    return jsonify(result)


if __name__ == "__main__":
    init_db()
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=True)
