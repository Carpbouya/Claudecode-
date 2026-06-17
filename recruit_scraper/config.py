import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

BASE_URL = "https://www.r-agent.com"
SEARCH_URL = f"{BASE_URL}/kensaku/search/"

REQUEST_DELAY = (1.5, 3.0)
MAX_PAGES = 100
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

PREFECTURES = {
    "北海道": "hokkaido",
    "東京都": "tokyo",
    "神奈川県": "kanagawa",
    "大阪府": "osaka",
    "愛知県": "aichi",
    "福岡県": "fukuoka",
    "埼玉県": "saitama",
    "千葉県": "chiba",
    "兵庫県": "hyogo",
    "京都府": "kyoto",
    "広島県": "hiroshima",
    "宮城県": "miyagi",
    "静岡県": "shizuoka",
    "茨城県": "ibaraki",
    "新潟県": "niigata",
    "長野県": "nagano",
    "岐阜県": "gifu",
    "栃木県": "tochigi",
    "群馬県": "gunma",
    "岡山県": "okayama",
    "三重県": "mie",
    "熊本県": "kumamoto",
    "鹿児島県": "kagoshima",
    "沖縄県": "okinawa",
}

JOB_CATEGORIES = {
    "IT・エンジニア": "it-engineer",
    "営業": "sales",
    "事務・管理": "admin",
    "企画・マーケティング": "planning",
    "経理・財務": "accounting",
    "人事・総務": "hr",
    "製造・技術": "manufacturing",
    "医療・介護": "medical",
    "建設・不動産": "construction",
    "物流・運輸": "logistics",
    "販売・サービス": "retail",
    "コンサルタント": "consultant",
}

DB_PATH = os.path.join(DATA_DIR, "jobs.db")
CSV_EXPORT_PATH = os.path.join(DATA_DIR, "jobs_export.csv")
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000
