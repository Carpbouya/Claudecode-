import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import BASE_URL, PREFECTURES


def parse_salary(text: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    cleaned = text.replace(",", "").replace("，", "").replace(" ", "")

    numbers = re.findall(r"(\d+)", cleaned)
    if not numbers:
        return None, None

    if "万" in text:
        vals = []
        for m in re.finditer(r"(\d+)万(\d+)?", cleaned):
            man = int(m.group(1))
            sub = int(m.group(2)) if m.group(2) else 0
            vals.append(man * 10000 + sub)
        if len(vals) >= 2:
            return vals[0], vals[1]
        elif len(vals) == 1:
            return vals[0], vals[0]

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

    cards = soup.select("[class*='jobCardContainer']")

    if not cards:
        cards = soup.select("[class*='jobCard___']")
    if not cards:
        cards = soup.select("a[href*='/viewjob/']")
        cards = [c.parent for c in cards]

    for card in cards:
        job = _parse_card(card, current_url, fallback_prefecture)
        if job:
            jobs.append(job)

    next_url = _find_next_page(soup, current_url)
    return jobs, next_url


def _parse_card(card, current_url: str, fallback_pref: str) -> dict | None:
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


def _find_next_page(soup: BeautifulSoup, current_url: str) -> str | None:
    # パターン1: rel="next"
    next_link = soup.select_one("a[rel='next']")
    if next_link and next_link.get("href"):
        href = next_link["href"]
        return href if href.startswith("http") else urljoin(BASE_URL, href)

    # パターン2: "次へ" や ">" テキストのリンク
    for link in soup.select("a[href]"):
        text = link.get_text(strip=True)
        if text in ("次へ", "次", "＞", ">", "›", "次のページ"):
            href = link.get("href", "")
            if href:
                return href if href.startswith("http") else urljoin(BASE_URL, href)

    # パターン3: aria-label="次のページ" など
    next_link = soup.select_one("a[aria-label*='次'], button[aria-label*='次']")
    if next_link and next_link.get("href"):
        href = next_link["href"]
        return href if href.startswith("http") else urljoin(BASE_URL, href)

    # パターン4: paginationコンテナ内の現在ページの次
    for container in soup.select("[class*='paginat'], [class*='Paginat'], [class*='pager'], [class*='Pager']"):
        current = container.select_one("[class*='current'], [class*='active'], [aria-current]")
        if current:
            next_sib = current.find_next_sibling("a")
            if next_sib and next_sib.get("href"):
                href = next_sib["href"]
                return href if href.startswith("http") else urljoin(BASE_URL, href)

    # パターン5: ?page=N のURL推測
    import re
    match = re.search(r'[?&]page=(\d+)', current_url)
    if match:
        current_page = int(match.group(1))
        next_page = current_page + 1
        return re.sub(r'([?&])page=\d+', f'\\1page={next_page}', current_url)

    # 初回ページ（pageパラメータなし）→ ?page=2 を試す
    if "page=" not in current_url:
        separator = "&" if "?" in current_url else "?"
        return f"{current_url}{separator}page=2"

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
