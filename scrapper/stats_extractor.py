import json
import os
import re
import time
import base64
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MatchStatsExtractor:
    """Extract match statistics from SofaScore pages, with API fallback."""

    def __init__(
        self,
        driver,
        *,
        user_agent: Optional[str] = None,
        api_base_url: str = "https://api.sofascore.com/api/v1",
    ):
        self.driver = driver
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.api_base_url = api_base_url.rstrip("/")
        self.debug = os.getenv("SCRAPER_DEBUG_STATS") == "1"

    def extract_match_statistics(self, match_number: int, match_url: Optional[str] = None) -> Dict:
        stats: Dict[str, object] = {"match_number": match_number}

        dom_stats = self._extract_from_dom()
        if dom_stats:
            stats.update(dom_stats)

        if len(stats) <= 1 and match_url:
            event_id = self._extract_event_id(match_url)
            if event_id:
                cdp_stats = self._extract_from_network_logs(event_id)
                if cdp_stats:
                    stats.update(cdp_stats)

        if len(stats) <= 1 and match_url:
            api_stats = self._extract_from_api(match_url)
            if api_stats:
                stats.update(api_stats)

        return stats

    def _open_statistics_tab(self) -> bool:
        self._ensure_network_enabled()

        selectors = [
            (By.CSS_SELECTOR, "a[href='#tab:statistics']"),
            (By.CSS_SELECTOR, "a[data-testid='statistics-tab']"),
            (
                By.XPATH,
                "//a[.//text()[contains(., 'Estatíst') or contains(., 'Statistics')]]",
            ),
        ]

        for by, selector in selectors:
            try:
                stats_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((by, selector))
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", stats_tab
                )
                self.driver.execute_script("arguments[0].click();", stats_tab)
                print("    Statistics tab opened")
                return True
            except Exception:
                continue

        print("    Statistics tab NOT found")
        return False

    def _extract_from_dom(self) -> Dict[str, str]:
        if not self._open_statistics_tab():
            return {}

        self._wait_for_stats_render()

        stat_rows = self._find_stat_rows()
        stats: Dict[str, str] = {}

        if stat_rows:
            stats_found = 0

            for row in stat_rows:
                try:
                    left_val, stat_name, right_val = self._parse_stat_row(row)
                    if not stat_name:
                        continue

                    clean_name = self._normalize_stat_name(stat_name)
                    if not clean_name:
                        continue

                    base_key = self._unique_stat_key(stats, clean_name)
                    stats[f"{base_key}_home"] = left_val
                    stats[f"{base_key}_away"] = right_val
                    stats_found += 1

                except Exception:
                    continue

            if stats_found:
                print(f"      Extracted {stats_found} statistics")
                return stats

        # Fallback: scan text blocks for value-label-value patterns
        scan_stats = self._scan_for_stat_lines()
        if scan_stats:
            print(f"      Extracted {len(scan_stats) // 2} statistics via text scan")
            return scan_stats

        if self.debug:
            stats_root = self._get_stats_root()
            try:
                preview = (stats_root.text or "") if stats_root else (self.driver.find_element(By.TAG_NAME, "body").text or "")
                preview_lines = [line for line in preview.splitlines() if line.strip()]
                print("      DEBUG: Stats text preview:")
                for line in preview_lines[:20]:
                    print(f"        {line}")
            except Exception:
                pass

        return {}

    def _wait_for_stats_render(self) -> None:
        try:
            WebDriverWait(self.driver, 10).until(
                lambda _driver: bool(self._find_stat_rows())
            )
            return
        except Exception:
            pass

        # Fallback: small delay and scroll to trigger lazy rendering
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
        except Exception:
            pass
        time.sleep(1)

    def _ensure_network_enabled(self) -> None:
        try:
            self.driver.execute_cdp_cmd("Network.enable", {})
        except Exception:
            pass

    def _drain_performance_logs(self) -> None:
        try:
            self.driver.get_log("performance")
        except Exception:
            pass

    def _get_performance_logs(self) -> List[Dict]:
        try:
            return self.driver.get_log("performance") or []
        except Exception:
            return []

    def _get_response_body_json(self, request_id: str) -> Optional[Dict]:
        try:
            response = self.driver.execute_cdp_cmd(
                "Network.getResponseBody", {"requestId": request_id}
            )
        except Exception:
            return None

        body = response.get("body") if isinstance(response, dict) else None
        if not body:
            return None

        if response.get("base64Encoded"):
            try:
                body = base64.b64decode(body).decode("utf-8", errors="replace")
            except Exception:
                return None

        try:
            return json.loads(body)
        except Exception:
            return None

    def _extract_from_network_logs(self, event_id: int) -> Dict[str, str]:
        """Extract match statistics by capturing the JSON response from Chrome's network logs."""
        patterns = [
            f"/event/{int(event_id)}/statistics",
            f"/api/v1/event/{int(event_id)}/statistics",
        ]

        start = time.time()
        seen_request_ids = set()

        while time.time() - start < 8:
            logs_raw = self._get_performance_logs()
            if not logs_raw:
                time.sleep(0.25)
                continue

            for entry in logs_raw:
                try:
                    msg = json.loads(entry.get("message", "{}")).get("message", {})
                except Exception:
                    continue

                method = msg.get("method")
                params = msg.get("params") or {}
                request_id = params.get("requestId")
                url = ""

                if method == "Network.responseReceived":
                    response = params.get("response") or {}
                    url = (response.get("url")) or ""
                    if self.debug and url and any(p in url for p in patterns):
                        status = response.get("status")
                        print(f"      DEBUG: stats response url={url} status={status}")
                elif method == "Network.requestWillBeSent":
                    url = ((params.get("request") or {}).get("url")) or ""
                elif method == "Network.requestWillBeSentExtraInfo":
                    headers = params.get("headers") or {}
                    path = headers.get(":path") or ""
                    authority = headers.get(":authority") or ""
                    scheme = headers.get(":scheme") or "https"
                    if authority and path:
                        url = f"{scheme}://{authority}{path}"
                    else:
                        url = path

                if not request_id or not url:
                    continue

                if not any(p in url for p in patterns):
                    continue

                if request_id in seen_request_ids:
                    continue
                seen_request_ids.add(request_id)

                data = self._get_response_body_json(request_id)
                if not data:
                    continue

                stats = self._flatten_api_stats(data or {})
                if stats:
                    print(f"      Extracted {len(stats) // 2} statistics via CDP network logs")
                    return stats

            time.sleep(0.25)

        return {}

    def _get_stats_root(self):
        container_selectors = [
            "div[data-testid='statistics-tab-panel']",
            "div[id*='statistics']",
            "div[class*='statistics']",
            "section[class*='statistics']",
        ]

        stats_root = None
        for selector in container_selectors:
            try:
                elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elems:
                    if elem.is_displayed():
                        stats_root = elem
                        break
            except Exception:
                continue
            if stats_root:
                break
        return stats_root

    def _find_stat_rows(self) -> List:
        stats_root = self._get_stats_root()
        search_root = stats_root if stats_root else self.driver

        row_selectors = [
            "[data-testid='statRow']",
            "[data-testid='match-statistics-row']",
            "[data-testid='match-statistics-row-home']",
            "div[class*='statRow']",
            "div[class*='statisticRow']",
            "div[class*='statsRow']",
            "div[class*='stat']",
            "div[class*='row']",
        ]

        for selector in row_selectors:
            try:
                rows = search_root.find_elements(By.CSS_SELECTOR, selector)
                rows = [row for row in rows if row.text and row.text.strip()]
                if rows:
                    return rows
            except Exception:
                continue

        return []

    def _parse_stat_row(self, row) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        selectors_home = [
            "[data-testid='stat-value-home']",
            "[data-testid='stat-home']",
            "[data-testid='home-value']",
            "span[class*='home']",
            "div[class*='home']",
        ]
        selectors_away = [
            "[data-testid='stat-value-away']",
            "[data-testid='stat-away']",
            "[data-testid='away-value']",
            "span[class*='away']",
            "div[class*='away']",
        ]
        selectors_label = [
            "[data-testid='stat-label']",
            "[data-testid='stat-name']",
            "[data-testid='stat-title']",
            "span[class*='name']",
            "div[class*='name']",
            "span[class*='label']",
            "div[class*='label']",
        ]

        left_val = self._first_text(row, selectors_home)
        right_val = self._first_text(row, selectors_away)
        stat_name = self._first_text(row, selectors_label)

        if (
            left_val
            and right_val
            and stat_name
            and self._looks_like_value(left_val)
            and self._looks_like_value(right_val)
            and self._looks_like_label(stat_name)
        ):
            return left_val, stat_name, right_val

        text_elements = row.find_elements(By.CSS_SELECTOR, "div, span")
        texts = [elem.text.strip() for elem in text_elements if elem.text and elem.text.strip()]

        if len(texts) < 3:
            return None, None, None

        for i in range(len(texts) - 2):
            left_val = texts[i]
            stat_name = texts[i + 1]
            right_val = texts[i + 2]

            if (
                self._looks_like_value(left_val)
                and self._looks_like_value(right_val)
                and self._looks_like_label(stat_name)
            ):
                return left_val, stat_name, right_val

        return None, None, None

    def _first_text(self, parent, selectors: List[str]) -> Optional[str]:
        for selector in selectors:
            try:
                elem = parent.find_element(By.CSS_SELECTOR, selector)
                text = elem.text.strip()
                if text:
                    return text
            except Exception:
                continue
        return None

    def _looks_like_value(self, text: str) -> bool:
        if not text:
            return False
        if text in {"-", "—", "–"}:
            return True
        return bool(re.search(r"\d", text)) or text == "0"

    def _looks_like_label(self, text: str) -> bool:
        if not text:
            return False
        return bool(re.search(r"[A-Za-zÀ-ÿ]", text))

    def _normalize_stat_name(self, stat_name: str) -> str:
        clean_name = stat_name.strip().lower()
        clean_name = clean_name.replace("%", "pct").replace("/", "_")
        clean_name = re.sub(r"\s+", "_", clean_name)
        clean_name = re.sub(r"[^\w_]", "", clean_name)
        return clean_name

    def _unique_stat_key(self, stats: Dict[str, str], base_key: str) -> str:
        key = base_key
        suffix = 2
        while f"{key}_home" in stats or f"{key}_away" in stats:
            key = f"{base_key}_{suffix}"
            suffix += 1
        return key

    def _scan_for_stat_lines(self) -> Dict[str, str]:
        stats_root = self._get_stats_root()
        search_root = stats_root if stats_root else self.driver

        try:
            raw_text = search_root.text or ""
        except Exception:
            raw_text = ""

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            return {}

        stats: Dict[str, str] = {}
        for i in range(len(lines) - 2):
            left_val = lines[i]
            stat_name = lines[i + 1]
            right_val = lines[i + 2]
            if (
                self._looks_like_value(left_val)
                and self._looks_like_value(right_val)
                and self._looks_like_label(stat_name)
            ):
                clean_name = self._normalize_stat_name(stat_name)
                if not clean_name:
                    continue
                base_key = self._unique_stat_key(stats, clean_name)
                stats[f"{base_key}_home"] = left_val
                stats[f"{base_key}_away"] = right_val

        return stats

    def _extract_event_id(self, match_url: str) -> Optional[int]:
        if not match_url:
            return None
        match = re.search(r"#id:(\d+)", match_url)
        if match:
            return int(match.group(1))
        match = re.search(r"/(\d+)$", match_url)
        if match:
            return int(match.group(1))
        return None

    def _unwrap_stat_value(self, value) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, dict):
            if "displayValue" in value:
                return str(value.get("displayValue"))
            if "value" in value:
                return str(value.get("value"))
            if "raw" in value:
                return str(value.get("raw"))
            if "text" in value:
                return str(value.get("text"))
        return str(value)

    def _extract_from_api(self, match_url: str) -> Dict[str, str]:
        event_id = self._extract_event_id(match_url)
        if not event_id:
            return {}

        base_urls = [
            self.api_base_url.rstrip("/"),
            "https://www.sofascore.com/api/v1",
        ]
        urls = [f"{base}/event/{event_id}/statistics" for base in base_urls]

        for url in urls:
            data = self._fetch_json(url)
            if data:
                stats = self._flatten_api_stats(data or {})
                if stats:
                    print(f"      Extracted {len(stats) // 2} statistics via API fallback")
                    return stats

        # Browser-context fallback (uses existing cookies/session)
        for url in urls:
            data = self._fetch_json_via_browser(url)
            if data:
                stats = self._flatten_api_stats(data or {})
                if stats:
                    print(f"      Extracted {len(stats) // 2} statistics via browser API fallback")
                    return stats

        return {}

    def _cookie_header(self) -> str:
        try:
            cookies = self.driver.get_cookies()
        except Exception:
            return ""

        cookie_parts = []
        for cookie in cookies:
            name = cookie.get("name")
            value = cookie.get("value")
            if name and value:
                cookie_parts.append(f"{name}={value}")
        return "; ".join(cookie_parts)

    def _fetch_json(self, url: str) -> Optional[Dict]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Referer": "https://www.sofascore.com/",
            "Origin": "https://www.sofascore.com",
        }

        cookie_header = self._cookie_header()
        if cookie_header:
            headers["Cookie"] = cookie_header

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                print(f"      WARNING: API stats fetch failed (HTTP {exc.code})")
            return None
        except Exception:
            return None

    def _fetch_json_via_browser(self, url: str) -> Optional[Dict]:
        script = """
            const url = arguments[0];
            const callback = arguments[1];
            fetch(url, { credentials: 'include' })
              .then(resp => {
                  if (!resp.ok) {
                      return callback({ __error: resp.status });
                  }
                  return resp.json().then(data => callback(data));
              })
              .catch(err => callback({ __error: String(err) }));
        """
        try:
            result = self.driver.execute_async_script(script, url)
        except Exception:
            return None

        if isinstance(result, dict) and result.get("__error"):
            return None
        if isinstance(result, dict):
            return result
        return None

    def _flatten_api_stats(self, raw: Dict) -> Dict[str, str]:
        out: Dict[str, str] = {}

        stats = raw.get("statistics")
        if isinstance(stats, list):
            blocks = stats
        elif isinstance(stats, dict):
            blocks = [stats]
        else:
            blocks = []

        for block in blocks:
            if not isinstance(block, dict):
                continue

            groups = (
                block.get("groups")
                or block.get("statisticsGroups")
                or block.get("periods")
                or []
            )
            if isinstance(groups, dict):
                groups = [groups]

            for group in groups or []:
                if not isinstance(group, dict):
                    continue

                group_name = (
                    group.get("groupName") or group.get("name") or group.get("title") or ""
                )
                group_key = self._normalize_stat_name(group_name) if group_name else ""

                items = (
                    group.get("statisticsItems")
                    or group.get("items")
                    or group.get("statistics")
                    or []
                )
                if isinstance(items, dict):
                    items = [items]

                for item in items or []:
                    if not isinstance(item, dict):
                        continue

                    name = item.get("name") or item.get("label") or item.get("title")
                    if not name:
                        continue

                    stat_key = self._normalize_stat_name(name)
                    key = f"{group_key}_{stat_key}" if group_key else stat_key

                    home = item.get("home")
                    away = item.get("away")

                    if home is None and "homeValue" in item:
                        home = item.get("homeValue")
                    if away is None and "awayValue" in item:
                        away = item.get("awayValue")
                    if home is None and "homeTeamValue" in item:
                        home = item.get("homeTeamValue")
                    if away is None and "awayTeamValue" in item:
                        away = item.get("awayTeamValue")

                    home_val = self._unwrap_stat_value(home)
                    away_val = self._unwrap_stat_value(away)

                    if home_val is None and away_val is None:
                        continue

                    base_key = key
                    suffix = 2
                    while f"{base_key}_home" in out or f"{base_key}_away" in out:
                        base_key = f"{key}_{suffix}"
                        suffix += 1

                    out[f"{base_key}_home"] = home_val if home_val is not None else "-"
                    out[f"{base_key}_away"] = away_val if away_val is not None else "-"

        return out
