"""
デモ用サンプルデータ生成

ダッシュボードの動作確認用にダミーの求人データを生成する。
"""

import random

from models import init_db, bulk_upsert_jobs

SAMPLE_COMPANIES = [
    ("株式会社サイバーエージェント", "IT・通信"),
    ("楽天グループ株式会社", "IT・通信"),
    ("株式会社リクルート", "サービス"),
    ("ソフトバンク株式会社", "IT・通信"),
    ("トヨタ自動車株式会社", "メーカー"),
    ("ソニーグループ株式会社", "メーカー"),
    ("株式会社NTTデータ", "IT・通信"),
    ("富士通株式会社", "IT・通信"),
    ("パナソニック株式会社", "メーカー"),
    ("日立製作所", "メーカー"),
    ("株式会社メルカリ", "IT・通信"),
    ("LINE株式会社", "IT・通信"),
    ("株式会社DeNA", "IT・通信"),
    ("株式会社野村総合研究所", "コンサルティング"),
    ("アクセンチュア株式会社", "コンサルティング"),
    ("PwCコンサルティング合同会社", "コンサルティング"),
    ("三菱UFJ銀行", "金融"),
    ("三井住友銀行", "金融"),
    ("キーエンス", "メーカー"),
    ("ファーストリテイリング", "小売"),
]

SAMPLE_TITLES = {
    "IT・エンジニア": [
        "バックエンドエンジニア",
        "フロントエンドエンジニア",
        "インフラエンジニア",
        "データサイエンティスト",
        "SRE/DevOpsエンジニア",
        "セキュリティエンジニア",
        "機械学習エンジニア",
        "iOSエンジニア",
        "Androidエンジニア",
        "テックリード",
    ],
    "営業": [
        "法人営業",
        "IT営業",
        "ソリューション営業",
        "アカウントマネージャー",
        "営業マネージャー",
    ],
    "企画・マーケティング": [
        "プロダクトマネージャー",
        "事業企画",
        "マーケティングマネージャー",
        "デジタルマーケティング",
        "ブランドマネージャー",
    ],
    "コンサルタント": [
        "ITコンサルタント",
        "戦略コンサルタント",
        "業務改善コンサルタント",
        "DXコンサルタント",
    ],
    "経理・財務": [
        "経理マネージャー",
        "財務アナリスト",
        "管理会計",
        "経理スタッフ",
    ],
}

SKILLS_BY_CATEGORY = {
    "IT・エンジニア": [
        "Python", "Java", "JavaScript", "TypeScript", "Go", "AWS", "Docker",
        "Kubernetes", "React", "Vue", "SQL", "Git", "CI/CD", "Linux",
        "PostgreSQL", "MongoDB", "Redis", "Terraform",
    ],
    "営業": ["法人営業経験", "マネジメント", "英語", "TOEIC"],
    "企画・マーケティング": [
        "プロジェクトマネジメント", "データ分析", "SQL", "英語", "マネジメント",
    ],
    "コンサルタント": [
        "プロジェクトマネジメント", "英語", "データ分析", "SQL", "Python",
    ],
    "経理・財務": ["簿記", "会計", "税務", "英語"],
}

PREFECTURES = ["東京都", "大阪府", "愛知県", "福岡県", "神奈川県", "埼玉県",
               "千葉県", "北海道", "兵庫県", "京都府", "広島県", "宮城県"]

WORK_STYLES = ["オフィス勤務", "リモート可", "フルリモート", "ハイブリッド", "週3リモート"]
EMPLOYMENT_TYPES = ["正社員", "契約社員", "正社員（試用期間あり）"]

SALARY_RANGES = {
    "IT・エンジニア": (400, 1200),
    "営業": (350, 900),
    "企画・マーケティング": (400, 1000),
    "コンサルタント": (500, 1500),
    "経理・財務": (350, 800),
}


def generate_demo_data(count: int = 500):
    init_db()
    jobs = []

    for i in range(count):
        category = random.choice(list(SAMPLE_TITLES.keys()))
        company, industry = random.choice(SAMPLE_COMPANIES)
        title = random.choice(SAMPLE_TITLES[category])
        pref = random.choice(PREFECTURES)
        sal_range = SALARY_RANGES[category]
        salary_min = random.randint(sal_range[0] // 50, sal_range[1] // 100) * 50
        salary_max = salary_min + random.randint(50, 300)

        skills = random.sample(
            SKILLS_BY_CATEGORY.get(category, []),
            k=min(random.randint(2, 5), len(SKILLS_BY_CATEGORY.get(category, [])))
        )

        work_style = random.choice(WORK_STYLES)
        emp_type = random.choice(EMPLOYMENT_TYPES)
        exp_years = f"{random.randint(1, 10)}年以上"

        jobs.append({
            "source_url": f"https://www.r-agent.com/job/demo-{i+1:05d}",
            "title": f"{title}【{company}】",
            "company_name": company,
            "industry": industry,
            "job_category": category,
            "salary_min": salary_min * 10000,
            "salary_max": salary_max * 10000,
            "salary_text": f"{salary_min}万円〜{salary_max}万円",
            "location": pref,
            "prefecture": pref,
            "work_style": work_style,
            "required_skills": ", ".join(skills),
            "preferred_skills": "",
            "experience_years": exp_years,
            "employment_type": emp_type,
            "description": f"{company}にて{title}として活躍いただきます。",
            "benefits": "各種社会保険完備、交通費支給、退職金制度",
        })

    bulk_upsert_jobs(jobs)
    print(f"デモデータ {count} 件を生成しました。")


if __name__ == "__main__":
    generate_demo_data()
