# news_sync.py
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

import feedparser
import requests

# נסה לטעון trafilatura (לא חובה)
try:
    import trafilatura
    HAS_TRAFI = True
except Exception:
    HAS_TRAFI = False

# ----------------------- קונפיגורציה -----------------------
SEEN_DB_PATH = "seen.json"        # קובץ דה-דופליקציה + זמן קליטה
REQUEST_TIMEOUT = 20              # טיימאאוט לבקשות HTTP (שניות)
HTTP_HEADERS = {"User-Agent": "NewsSync/1.0 (+https://example.local)"}  # UA ידידותי
SITEMAP_MAX_DEPTH = 2             # עד כמה עמוק לרדת ב-sitemap index
SITEMAP_MAX_CHILDREN = 50         # כמה קבצי sitemap-ילד לבדוק מכל אינדקס
# ------------------------------------------------------------

def _now_local_iso() -> str:
    """זמן נוכחי בפורמט ISO-8601 לפי שעון מקומי (כולל offset)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")

def _load_seen() -> Dict[str, str]:
    """טען מילון {url: first_seen_iso} מ-seen.json."""
    if os.path.exists(SEEN_DB_PATH):
        try:
            with open(SEEN_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}

def _save_seen(seen: Dict[str, str]) -> None:
    """שמור את מילון הכתובות שנראו (atomically)."""
    tmp = SEEN_DB_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SEEN_DB_PATH)

def _extract_text(url: str):
    """
    נסה לחלץ טקסט מלא וכותרת.
    1) מוריד HTML עם requests (User-Agent)
    2) מנסה trafilatura.extract על ה-HTML
    3) אם trafilatura לא זמינה/נכשל -> מחזיר לפחות כותרת מ-meta
    """
    # 1) הורדה יציבה עם requests
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        html = r.text
    except Exception:
        return (None, None)

    # 2) trafilatura (אם מותקנת)
    if HAS_TRAFI:
        try:
            out = trafilatura.extract(
                html,
                output_format="json",
                with_metadata=True,
                url=url,                 # עוזר למטאדאטה/נרמול לינקים
                include_comments=False,
            )
            if out:
                data = json.loads(out)
                return (data.get("title"), data.get("text"))
        except Exception:
            pass

    # 3) fallback: החזרת כותרת מה-HTML (meta og:title/title)
    try:
        from bs4 import BeautifulSoup  # pip install beautifulsoup4
        soup = BeautifulSoup(html, "html.parser")
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            return (og["content"].strip(), None)
        if soup.title and soup.title.text:
            return (soup.title.text.strip(), None)
    except Exception:
        pass

    return (None, None)

# ----------------------- RSS -----------------------
def _check_rss(source_url: str, label: str, seen: Dict[str, str]) -> List[dict]:
    """
    קורא פיד RSS ומחזיר פריטים *חדשים בלבד*.
    כל פריט: dict עם url, title, published, seen_at, source_label, text (אם קיים).
    """
    out: List[dict] = []

    # feedparser לא תומך ישירות בכותרות/טיימאאוט—אבל נסה קודם HEAD/GET לוודא נגישות
    try:
        r = requests.get(source_url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        # נחזיר אירוע שגיאה "רך" למעלה בשכבת הקריאה
        raise RuntimeError(f"RSS request failed: {e}")

    parsed = feedparser.parse(r.content)
    if getattr(parsed, "bozo", False) and getattr(parsed, "bozo_exception", None):
        # לא מפיל את כל הסבב—מחזיר כחריגה שתיתפס ב-check_updates
        raise RuntimeError(f"RSS parse error: {parsed.bozo_exception}")

    for entry in getattr(parsed, "entries", []):
        url = entry.get("link") or entry.get("id")
        if not url or url in seen:
            continue

        seen_at = _now_local_iso()
        seen[url] = seen_at

        title = entry.get("title")
        published = entry.get("published") or entry.get("updated")

        # חילוץ טקסט מלא (לא חובה)
        t_title, t_text = _extract_text(url)
        if t_title:
            title = t_title

        out.append({
            "url": url,
            "title": title,
            "published": published,     # תאריך מהפיד (אם יש)
            "seen_at": seen_at,         # מתי אנחנו קלטנו את הכתבה
            "source_label": label,
            "text": t_text,             # טקסט מלא אם נמצא
            "source_type": "rss",
        })

    return out

# ----------------------- Sitemap -----------------------
def _iter_sitemap_urls(sitemap_url: str, depth: int = 0):
    """
    איטרציה על כל ה-URLs בסייטמאפ.
    תומך גם ב-sitemap index באופן רקורסיבי עד עומק SITEMAP_MAX_DEPTH.
    """
    try:
        r = requests.get(sitemap_url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception:
        return

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    # אם זה אינדקס של סייטמאפים
    sitems = root.findall("sm:sitemap", ns)
    if sitems:
        if depth >= SITEMAP_MAX_DEPTH:
            return
        count = 0
        for sm in sitems:
            loc_el = sm.find("sm:loc", ns)
            if loc_el is not None and loc_el.text:
                yield from _iter_sitemap_urls(loc_el.text.strip(), depth=depth + 1)
                count += 1
                if count >= SITEMAP_MAX_CHILDREN:
                    break
        return

    # אחרת: urlset רגיל
    for url_el in root.findall("sm:url", ns):
        loc_el = url_el.find("sm:loc", ns)
        if loc_el is not None and loc_el.text:
            yield loc_el.text.strip()

def _check_sitemap(sitemap_url: str, label: str, seen: Dict[str, str]) -> List[dict]:
    """
    קורא sitemap ומחזיר פריטים *חדשים בלבד* (דומה ל-RSS).
    """
    out: List[dict] = []
    for url in _iter_sitemap_urls(sitemap_url):
        if not url or url in seen:
            continue

        seen_at = _now_local_iso()
        seen[url] = seen_at

        t_title, t_text = _extract_text(url)

        out.append({
            "url": url,
            "title": t_title,          # כותרת מתוך חילוץ (אם הצליח)
            "published": None,         # בסייטמאפ לרוב אין תאריך כתבה זמין
            "seen_at": seen_at,
            "source_label": label,
            "text": t_text,
            "source_type": "sitemap",
        })
    return out

# ----------------------- API פנימי לשימוש בקוד שלך -----------------------
def check_updates(sources: List[dict]) -> List[dict]:
    """
    נקודת כניסה: בכל קריאה קוראת את כל המקורות, מחזירה כתבות חדשות,
    ומעדכנת seen.json עם זמן קליטה (seen_at).
    sources: [{"type": "rss"|"sitemap", "url": "...", "label": "שם"}]
    """
    seen = _load_seen()
    new_items: List[dict] = []

    for src in sources:
        st = (src.get("type") or "").lower()
        url = src.get("url")
        label = src.get("label") or url
        if not url or st not in ("rss", "sitemap"):
            continue
        try:
            if st == "rss":
                new_items.extend(_check_rss(url, label, seen))
            else:
                new_items.extend(_check_sitemap(url, label, seen))
        except Exception as e:
            # לא מפיל את כל הבדיקה אם מקור אחד נכשל—רק מדווח
            new_items.append({
                "url": None,
                "title": None,
                "published": None,
                "seen_at": _now_local_iso(),
                "source_label": label,
                "text": None,
                "source_type": st,
                "error": f"{type(e).__name__}: {e}",
            })

    if new_items:
        _save_seen(seen)
    return new_items

# ----------------------- דוגמת שימוש ישירה -----------------------
if __name__ == "__main__":
    SOURCES = [
        {"type": "rss", "url": "http://rss.cnn.com/rss/cnn_topstories.rss", "label": "CNN Top"},
        {"type": "sitemap", "url": "https://www.n12.co.il/sitemap.xml", "label": "N12"},
        {"type": "rss", "url": "https://www.ynet.co.il/Integration/StoryRss2.xml", "label": "Ynet"},
    ]

    print("בודק עדכונים...")
    items = check_updates(SOURCES)
    if not items:
        print("אין כתבות חדשות כרגע.")
    else:
        for i, it in enumerate(items, 1):
            print(f"\n[{i}] {it.get('source_label')} — {it.get('title') or '(ללא כותרת)'}")
            print("URL:", it.get("url"))
            print("published:", it.get("published"))
            print("seen_at :", it.get("seen_at"))
            if it.get("text"):
                t = it["text"]
                print("text (first 400):", (t[:400] + ("..." if len(t) > 400 else "")))
