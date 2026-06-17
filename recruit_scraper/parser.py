import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import BASE_URL, PREFECTURES


def parse_salary(text: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    cleaned = text.replace(",", "").replace("，", "").replace(" ", "")

    multiplier = _detect_salary_multiplier(text)

    numbers = re.findall(r"(\d+)", cleaned)
    if not numbers:
        return None, None

    if "万" in text:
        vals = []
        for m in re.finditer(r"(\d+)万(\d+)?", cleaned):
            man = int(m.group(1))
            sub = int(m.group(2)) if m.group(2) else 0
            vals.append((man * 10000 + sub) * multiplier)
        if len(vals) >= 2:
            return int(vals[0]), int(vals[1])
        elif len(vals) == 1:
            return int(vals[0]), int(vals[0])

    if len(numbers) >= 2:
        a, b = int(numbers[0]), int(numbers[1])
        if a > 10000:
            return int(a * multiplier), int(b * multiplier)
        return int(a * 10000 * multiplier), int(b * 10000 * multiplier)
    val = int(numbers[0])
    if val > 10000:
        return int(val * multiplier), int(val * multiplier)
    return int(val * 10000 * multiplier), int(val * 10000 * multiplier)


def _detect_salary_multiplier(text: str) -> float:
    if "年収" in text or "年俸" in text:
        return 1
    if "月給" in text or "月収" in text:
        return 14
    if "日給" in text:
        return 260
    if "時給" in text:
        return 2080
    # 金額が100万以上なら年収扱い、未満なら月給扱い
    nums = re.findall(r"(\d+)万", text)
    if nums and int(nums[0]) >= 100:
        return 1
    if nums:
        return 14
    return 1


def detect_prefecture(text: str) -> str:
    if not text:
        return ""
    for pref in PREFECTURES:
        if pref in text:
            return pref
    return ""


def parse_listing_page(html: str, current_url: str,
                        fallback_prefecture: str = "") -> tuple[list[dict], str | None]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    cards = soup.select("a[href*='/viewjob/']")

    for card in cards:
        job = _parse_card(card, current_url, fallback_prefecture)
        if job:
            jobs.append(job)

    next_url = _find_next_page(soup, current_url)
    return jobs, next_url


def _parse_card(card, current_url: str, fallback_pref: str) -> dict | None:
    if card.name == "a" and "/viewjob/" in card.get("href", ""):
        href = card.get("href", "")
    else:
        link_elem = card.select_one("a[href*='/viewjob/']")
        if not link_elem:
            return None
        href = link_elem.get("href", "")
    if href and not href.startswith("http"):
        href = urljoin(BASE_URL, href)

    company_elem = card.select_one("[class*='corpName']")
    company = company_elem.get_text(strip=True) if company_elem else ""

    title_elem = card.select_one("[class*='jobTitle']")
    title = title_elem.get_text(strip=True) if title_elem else ""
    if not title:
        return None

    desc_elem = card.select_one("[class*='subTitle']")
    desc = desc_elem.get_text(strip=True) if desc_elem else ""

    emp_type_elem = card.select_one("[class*='jobType']")
    emp_type = emp_type_elem.get_text(strip=True) if emp_type_elem else ""

    salary_title_elem = card.select_one("[class*='salaryTitle']")
    salary_title = salary_title_elem.get_text(strip=True) if salary_title_elem else ""

    salary_elem = card.select_one("[class*='mainSalary']")
    salary_text_raw = salary_elem.get_text(strip=True) if salary_elem else ""
    salary_text = f"{salary_title}{salary_text_raw}" if salary_title else salary_text_raw

    salary_min, salary_max = parse_salary(salary_text)

    location_elem = card.select_one(
        "[class*='jobLocation'], [class*='jobLocat'], [class*='address']"
    )
    location = location_elem.get_text(strip=True) if location_elem else ""
    location = location.replace("勤務地", "").strip()

    prefecture = detect_prefecture(location) or fallback_pref

    category_elem = card.select_one("[class*='jobCategory'], [class*='occupation']")
    category = category_elem.get_text(strip=True) if category_elem else ""

    return {
        "source_url": href,
        "title": title,
        "company_name": company,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_text": salary_text,
        "location": location,
        "prefecture": prefecture,
        "job_category": category,
        "description_summary": desc[:500] if desc else "",
    }


def _is_valid_next_url(href: str) -> bool:
    if not href:
        return False
    full = href if href.startswith("http") else urljoin(BASE_URL, href)
    return "area-" in full or "cursor=" in full or "page=" in full


def _to_full_url(href: str) -> str:
    return href if href.startswith("http") else urljoin(BASE_URL, href)


def _find_next_page(soup: BeautifulSoup, current_url: str) -> str | None:
    # パターン1: rel="next"
    next_link = soup.select_one("a[rel='next']")
    if next_link and next_link.get("href") and _is_valid_next_url(next_link["href"]):
        return _to_full_url(next_link["href"])

    # パターン2: "次へ" テキストのリンク
    for link in soup.select("a[href]"):
        text = link.get_text(strip=True)
        if text in ("次へ", "次", "＞", ">", "›", "次のページ"):
            href = link.get("href", "")
            if _is_valid_next_url(href):
                return _to_full_url(href)

    # パターン3: aria-label="次のページ"
    next_link = soup.select_one("a[aria-label*='次']")
    if next_link and next_link.get("href") and _is_valid_next_url(next_link["href"]):
        return _to_full_url(next_link["href"])

    # パターン4: cursorリンクを探す（このサイトのページネーション方式）
    for link in soup.select("a[href*='cursor=']"):
        href = link.get("href", "")
        if href and "area-" in href:
            return _to_full_url(href)

    return None


def parse_detail_page(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    detail = {}

    rows = soup.select(
        "table tr, dl, [class*='detail'], [class*='Detail'], "
        "[class*='tableRow'], [class*='infoItem']"
    )
    for row in rows:
        header = row.select_one("th, dt, [class*='label'], [class*='Label'], [class*='heading']")
        value = row.select_one("td, dd, [class*='value'], [class*='Value'], [class*='content']")
        if not header or not value:
            continue
        h = header.get_text(strip=True)
        v = value.get_text(strip=True)

        if "必須" in h or "応募資格" in h or "必要" in h:
            detail["required_skills"] = v
        elif "歓迎" in h or "あれば" in h or "尚可" in h:
            detail["preferred_skills"] = v
        elif "経験" in h and ("年" in v or "以上" in v):
            detail["experience_years"] = v
        elif "雇用形態" in h:
            detail["employment_type"] = v
        elif "業種" in h or "業界" in h:
            detail["industry"] = v
        elif "勤務地" in h:
            detail["location"] = v
        elif "年収" in h or "給与" in h:
            detail["salary_text"] = v
        elif "福利" in h or "待遇" in h:
            detail["benefits"] = v
        elif "リモート" in h or "在宅" in h or "テレワーク" in h:
            detail["work_style"] = v
        elif "仕事内容" in h or "業務内容" in h:
            detail["description"] = v

    return detail


def get_total_count(html: str) -> int | None:
    soup = BeautifulSoup(html, "lxml")
    result_info = soup.select_one("[class*='resultInfo'], [class*='ResultInfo']")
    if result_info:
        text = result_info.get_text(strip=True)
        nums = re.findall(r'([\d,]+)', text)
        for n in nums:
            val = int(n.replace(",", ""))
            if val > 0:
                return val

    text = soup.get_text()
    match = re.search(r"([\d,]+)\s*件", text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None
