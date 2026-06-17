import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import BASE_URL, PREFECTURES


def parse_salary(text: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    cleaned = text.replace(",", "").replace("，", "")
    numbers = re.findall(r"(\d+)", cleaned)
    if not numbers:
        return None, None

    if "万" in text:
        if len(numbers) >= 2:
            return int(numbers[0]) * 10000, int(numbers[1]) * 10000
        return int(numbers[0]) * 10000, int(numbers[0]) * 10000

    if len(numbers) >= 2:
        a, b = int(numbers[0]), int(numbers[1])
        if a > 10000:
            return a, b
        return a * 10000, b * 10000
    val = int(numbers[0])
    if val > 10000:
        return val, val
    return val * 10000, val * 10000


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

    selectors = [
        ".cassetteRecruit",
        ".cassetteRecruit__content",
        ".job-card",
        ".search-result-item",
        ".job-list-item",
        "[class*='jobCard']",
        "[class*='JobCard']",
        "[class*='result-item']",
        "article.job",
    ]
    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if cards:
            break

    if not cards:
        cards = soup.select("article, .card")
        cards = [c for c in cards if c.select_one("a[href]")]

    for card in cards:
        job = _parse_card(card, current_url, fallback_prefecture)
        if job:
            jobs.append(job)

    next_url = _find_next_page(soup)
    return jobs, next_url


def _parse_card(card, current_url: str, fallback_pref: str) -> dict | None:
    title_selectors = [
        "h2 a", "h3 a", ".job-title a", ".jobTitle a",
        "[class*='title'] a", "[class*='Title'] a",
        "h2", "h3", ".job-title", ".jobTitle",
    ]
    title_elem = None
    for sel in title_selectors:
        title_elem = card.select_one(sel)
        if title_elem:
            break

    title = title_elem.get_text(strip=True) if title_elem else None
    if not title:
        return None

    link = None
    if title_elem and title_elem.name == "a":
        link = title_elem.get("href", "")
    elif title_elem:
        a = title_elem.find("a")
        if a:
            link = a.get("href", "")
    if not link:
        first_link = card.select_one("a[href]")
        if first_link:
            link = first_link.get("href", "")

    if link and not link.startswith("http"):
        link = urljoin(BASE_URL, link)

    company = _extract_text(card, [
        ".company-name", ".companyName", "[class*='company']",
        "[class*='Company']", ".corp-name",
    ])

    salary_text = _extract_text(card, [
        ".salary", ".income", "[class*='salary']", "[class*='Salary']",
        "[class*='income']", "[class*='年収']",
    ])
    salary_min, salary_max = parse_salary(salary_text)

    location = _extract_text(card, [
        ".location", ".area", "[class*='location']", "[class*='Location']",
        "[class*='area']", "[class*='勤務地']",
    ])
    prefecture = detect_prefecture(location) or fallback_pref

    category = _extract_text(card, [
        ".category", ".job-type", "[class*='category']",
        "[class*='Category']", "[class*='職種']",
    ])

    desc = _extract_text(card, [
        ".description", ".job-desc", "[class*='description']",
        "[class*='Description']", ".summary",
    ])

    return {
        "source_url": link or current_url,
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


def _extract_text(element, selectors: list[str]) -> str:
    for sel in selectors:
        found = element.select_one(sel)
        if found:
            return found.get_text(strip=True)
    return ""


def _find_next_page(soup: BeautifulSoup) -> str | None:
    for sel in ["a.next", "a[rel='next']", ".pagination .next a", ".pager .next a"]:
        link = soup.select_one(sel)
        if link and link.get("href"):
            href = link["href"]
            return href if href.startswith("http") else urljoin(BASE_URL, href)

    for link in soup.select(".pagination a, .pager a, [class*='page'] a"):
        text = link.get_text(strip=True)
        if text in ("次へ", "次", "＞", ">", "›", ">>"):
            href = link.get("href", "")
            if href:
                return href if href.startswith("http") else urljoin(BASE_URL, href)
    return None


def parse_detail_page(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    detail = {}

    rows = soup.select("table tr, dl, .detail-section, .job-detail-section")
    for row in rows:
        header = row.select_one("th, dt, .label, .item-label")
        value = row.select_one("td, dd, .value, .item-value")
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
    for el in soup.select("[class*='count'], [class*='Count'], [class*='total'], .result-num"):
        text = el.get_text(strip=True)
        nums = re.findall(r"[\d,]+", text)
        for n in nums:
            val = int(n.replace(",", ""))
            if val > 0:
                return val
    text = soup.get_text()
    match = re.search(r"([\d,]+)\s*件", text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None
