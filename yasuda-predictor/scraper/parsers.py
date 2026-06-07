"""netkeiba HTML パーサー（純粋関数）。

I/O を一切持たない。HTML 文字列を受け取りモデル/プリミティブを返すため、
保存した HTML フィクスチャでオフライン単体テストが可能。

netkeiba は DOM が頻繁に変わるため、可能な限り「ヘッダのラベル → 列インデックス」
方式や複数セレクタのフォールバックで堅牢化している。各パーサ冒頭に対象構造を記載。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Horse, JockeyStats, PastResult, SireStats

# 既知の競馬場名（開催文字列 "2東京5" 等から抽出）
COURSES = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]


# -- 共通ヘルパ -------------------------------------------------------------
def _text(node) -> str:
    return node.get_text(strip=True) if node else ""


def _to_int(s: str) -> int | None:
    m = re.search(r"-?\d+", s or "")
    return int(m.group()) if m else None


def _to_float(s: str) -> float | None:
    m = re.search(r"\d+(?:\.\d+)?", (s or "").replace(",", ""))
    return float(m.group()) if m else None


def _extract_id(href: str, kind: str) -> str:
    """href から netkeiba の各種 ID を抽出する。

    例: /horse/2019105212/ -> "2019105212"
        /jockey/result/recent/05339/ -> "05339"
        /horse/sire/2005103504/ -> "2005103504"
    """
    if not href:
        return ""
    patterns = {
        "horse": r"/horse/(?:ped/)?(\w+)",
        "sire": r"/horse/sire/(\w+)",
        "jockey": r"/jockey/(?:result/(?:recent/)?)?(\w+)",
    }
    # sire は /horse/sire/ を horse より優先
    if kind == "horse":
        m = re.search(r"/horse/(?!sire/|ped/)(\w+)", href)
        if m:
            return m.group(1)
    m = re.search(patterns[kind], href)
    return m.group(1) if m else ""


def _course_from(text: str) -> str:
    for c in COURSES:
        if c in (text or ""):
            return c
    return ""


def _surface_distance(text: str) -> tuple[str, int | None]:
    """"芝1600" / "ダ1200" / "障3000" -> (surface, distance)。"""
    t = text or ""
    surface = ""
    if "芝" in t:
        surface = "芝"
    elif "ダ" in t:
        surface = "ダート"
    elif "障" in t:
        surface = "障害"
    return surface, _to_int(t)


def _header_index(table) -> dict[str, int]:
    """テーブルのヘッダ行から「ラベル → 列インデックス」を作る。"""
    head = table.select_one("tr")
    if not head:
        return {}
    cells = head.find_all(["th", "td"])
    return {_text(c): i for i, c in enumerate(cells)}


# -- 出馬表 -----------------------------------------------------------------
def parse_shutuba(html: str) -> list[Horse]:
    """出馬表（race.netkeiba.com/race/shutuba.html）をパース。

    構造: table.Shutuba_Table > tr.HorseList
      td[class^=Waku] span      … 枠番
      td[class^=Umaban]         … 馬番
      span.HorseName a[/horse/] … 馬名 + horse_id
      td.Jockey a[/jockey/]     … 騎手 + jockey_id
      span[id^=odds-] / td.Popular span … 単勝オッズ
    """
    soup = BeautifulSoup(html, "html.parser")
    horses: list[Horse] = []
    rows = soup.select("table.Shutuba_Table tr.HorseList") or soup.select("tr.HorseList")
    for row in rows:
        try:
            frame = _to_int(_text(row.select_one("td[class^=Waku] span, td.Waku span")))
            number = _to_int(_text(row.select_one("td[class^=Umaban]")))
            name_a = row.select_one("span.HorseName a, td.HorseInfo a[href*='/horse/']")
            name = _text(name_a)
            horse_id = _extract_id(name_a.get("href", "") if name_a else "", "horse")
            jockey_a = row.select_one("td.Jockey a[href*='/jockey/']")
            jockey = _text(jockey_a)
            jockey_id = _extract_id(jockey_a.get("href", "") if jockey_a else "", "jockey")
            odds = _to_float(_text(row.select_one("span[id^=odds-], td.Popular span, td.Txt_R span")))
            if not name:
                continue
            horses.append(Horse(
                number=number or len(horses) + 1,
                frame=frame or 0,
                name=name,
                jockey=jockey,
                win_odds=odds or 0.0,
                horse_id=horse_id,
                jockey_id=jockey_id,
            ))
        except Exception:
            continue
    return horses


def parse_odds(html: str) -> dict[int, float]:
    """単勝オッズページ -> 馬番 → オッズ。"""
    soup = BeautifulSoup(html, "html.parser")
    result: dict[int, float] = {}
    for row in soup.select("tr"):
        num = _to_int(_text(row.select_one("td[class^=Umaban]")))
        odds = _to_float(_text(row.select_one("span[id^=odds-], td.Odds span, span.Odds")))
        if num and odds:
            result[num] = odds
    return result


# -- 馬ページ（過去成績・血統）---------------------------------------------
def parse_horse_results(html: str, *, limit: int = 12) -> list[PastResult]:
    """馬ページ（db.netkeiba.com/horse/{id}/）の過去成績テーブルをパース。

    構造: table.db_h_race_results（別名 race_table_01）
      ヘッダ: 日付/開催/.../距離/.../着順/頭数/人気 ...
    列はヘッダラベルでマッピングし、列順変更に耐性を持たせる。
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.db_h_race_results, table.race_table_01")
    if not table:
        return []
    idx = _header_index(table)

    def col(label: str) -> int | None:
        for k, v in idx.items():
            if label in k:
                return v
        return None

    c_date = col("日付")
    c_venue = col("開催")
    c_dist = col("距離")
    c_finish = col("着順")
    c_size = col("頭数")
    c_pop = col("人気")

    results: list[PastResult] = []
    for row in table.select("tr")[1:]:  # ヘッダ除く
        cells = row.find_all("td")
        if not cells:
            continue

        def get(i: int | None) -> str:
            return _text(cells[i]) if i is not None and i < len(cells) else ""

        surface, distance = _surface_distance(get(c_dist))
        finish = _to_int(get(c_finish))
        if distance is None or finish is None:
            continue
        results.append(PastResult(
            date=get(c_date),
            course=_course_from(get(c_venue)),
            surface=surface or "芝",
            distance=distance,
            finish=finish,
            field_size=_to_int(get(c_size)) or 0,
            popularity=_to_int(get(c_pop)) or 0,
        ))
        if len(results) >= limit:
            break
    return results


def parse_pedigree(html: str) -> tuple[str, str, str]:
    """馬ページの血統表をパースし (父, 母父, 父のhorse_id) を返す。

    構造: table.blood_table（3代血統表, 8 行）
      row0 先頭 a … 父
      row4 先頭 a … 母 / row4 2 番目 a … 母父
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.blood_table")
    if not table:
        return "", "", ""
    rows = table.find_all("tr")
    sire = sire_id = broodmare_sire = ""

    if rows:
        a = rows[0].find("a")
        if a:
            sire = _text(a)
            sire_id = _extract_id(a.get("href", ""), "horse")
    if len(rows) > 4:
        anchors = rows[4].find_all("a")
        if len(anchors) >= 2:
            broodmare_sire = _text(anchors[1])
        elif anchors:
            broodmare_sire = _text(anchors[0])
    return sire, broodmare_sire, sire_id


# -- 騎手ページ -------------------------------------------------------------
def parse_jockey_course_stats(html: str, *, course: str, surface: str = "") -> JockeyStats:
    """騎手ページ（db.netkeiba.com/jockey/{id}/）の競馬場別成績をパース。

    構造: 競馬場別成績テーブル（race_table_01）。各行 先頭セルに競馬場名、
      着別度数 1着/2着/3着/着外 列を持つ。course 行を合算する。
    """
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.select("table.race_table_01, table.nk_tb_common, table"):
        idx = _header_index(table)
        c_first = _find_col(idx, "1着")
        c_second = _find_col(idx, "2着")
        c_third = _find_col(idx, "3着")
        c_out = _find_col(idx, "着外")
        if c_first is None:
            continue
        for row in table.select("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            label = _text(cells[0])
            if course and course not in label:
                continue
            if surface and surface[0] not in label and ("芝" in label or "ダ" in label):
                # サーフェス分割テーブルなら一致行のみ採用
                continue
            wins = _cell_int(cells, c_first)
            second = _cell_int(cells, c_second)
            third = _cell_int(cells, c_third)
            out = _cell_int(cells, c_out)
            starts = wins + second + third + out
            if starts:
                return JockeyStats(starts=starts, wins=wins, shows=wins + second + third)
    return JockeyStats()


# -- 種牡馬ページ -----------------------------------------------------------
def parse_sire_course_stats(html: str, *, course: str, surface: str,
                            distance: int, distance_tolerance: int = 200) -> SireStats:
    """種牡馬ページ（db.netkeiba.com/horse/sire/{id}/）のコース/距離別成績をパース。

    course+surface かつ distance±許容幅 の行を合算。距離帯が無ければ
    course+surface 集計にフォールバックする。
    """
    soup = BeautifulSoup(html, "html.parser")
    best = SireStats()
    fallback = SireStats()
    for table in soup.select("table.race_table_01, table.nk_tb_common, table"):
        idx = _header_index(table)
        c_first = _find_col(idx, "1着")
        c_second = _find_col(idx, "2着")
        c_third = _find_col(idx, "3着")
        c_out = _find_col(idx, "着外")
        if c_first is None:
            continue
        for row in table.select("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            label = _text(cells[0])
            if course and course not in label:
                continue
            if surface and surface[0] not in label:
                continue
            wins = _cell_int(cells, c_first)
            second = _cell_int(cells, c_second)
            third = _cell_int(cells, c_third)
            out = _cell_int(cells, c_out)
            runs = wins + second + third + out
            if not runs:
                continue
            fallback = SireStats(fallback.runs + runs, fallback.wins + wins,
                                 fallback.shows + wins + second + third)
            row_dist = _to_int(label)
            if row_dist is not None and abs(row_dist - distance) <= distance_tolerance:
                best = SireStats(best.runs + runs, best.wins + wins,
                                 best.shows + wins + second + third)
    return best if best.runs else fallback


# -- 調教ページ -------------------------------------------------------------
def parse_training(html: str) -> dict[int, tuple[float | None, str]]:
    """調教ページ（race.netkeiba.com/race/oikiri.html）をパース。

    構造: table.OikiriTable > tr.HorseList
      td[class^=Umaban]  … 馬番
      td.Time / td.RapTime … 調教タイム（最後の数値を採用）
      td.Hyouka / td.Eval span … 評価（S/A/B/C → A/B/C へ正規化）
    戻り値: 馬番 → (タイム秒 | None, 評価)
    """
    soup = BeautifulSoup(html, "html.parser")
    result: dict[int, tuple[float | None, str]] = {}
    rows = soup.select("table.OikiriTable tr.HorseList") or soup.select("tr.HorseList")
    for row in rows:
        number = _to_int(_text(row.select_one("td[class^=Umaban]")))
        if not number:
            continue
        time = _to_float(_text(row.select_one("td.Time, td.RapTime, td.Oikiri_Time")))
        eval_text = _text(row.select_one("td.Hyouka, td.Eval, span.Eval_Mark, td.Eval_Mark"))
        result[number] = (time, _normalize_grade(eval_text))
    return result


# -- 内部ヘルパ -------------------------------------------------------------
def _find_col(idx: dict[str, int], label: str) -> int | None:
    for k, v in idx.items():
        if label in k:
            return v
    return None


def _cell_int(cells, i: int | None) -> int:
    if i is None or i >= len(cells):
        return 0
    return _to_int(_text(cells[i])) or 0


def _normalize_grade(text: str) -> str:
    t = (text or "").upper()
    if t.startswith("S") or t.startswith("A") or "好" in t:
        return "A"
    if t.startswith("B") or "良" in t:
        return "B"
    return "C"
