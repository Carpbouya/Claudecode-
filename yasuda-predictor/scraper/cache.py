"""ファイルベースのキャッシュ管理。

同一レースの再実行はキャッシュから即時返却し、netkeiba への過剰アクセスを避ける。
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


class HtmlCache:
    """URL 単位で取得 HTML を保存・再利用する。"""

    def __init__(self, ttl_sec: int, cache_dir: Path = CACHE_DIR) -> None:
        self.ttl_sec = ttl_sec
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, url: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{key}.html"

    def get(self, url: str) -> str | None:
        """有効期限内のキャッシュがあれば本文を返す。なければ None。"""
        path = self._path_for(url)
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > self.ttl_sec:
            return None
        return path.read_text(encoding="utf-8", errors="replace")

    def set(self, url: str, html: str) -> None:
        self._path_for(url).write_text(html, encoding="utf-8", errors="replace")

    def clear(self) -> int:
        """キャッシュを全削除し、削除件数を返す。"""
        count = 0
        for f in self.cache_dir.glob("*.html"):
            f.unlink()
            count += 1
        return count
