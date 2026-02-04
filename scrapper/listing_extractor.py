import re
from typing import Dict, Optional

from selenium.webdriver.common.by import By


class ListingExtractor:
    """Helpers for extracting match info from the opponent listing page."""

    def __init__(self, driver):
        self.driver = driver

    def extract_basic_info_from_listing(self, match_element) -> Dict:
        info: Dict[str, str] = {}
        row = self._get_match_row_element(match_element)

        # Score from explicit score elements
        score = self._extract_score_from_row(row)
        if score:
            info.update(score)

        # Fallback score from text
        if "home_score" not in info or "away_score" not in info:
            score_text = self._extract_score_from_text(row.text if row else "")
            if score_text:
                info.update(score_text)

        # Team names from images alt or text blocks
        team_names = []
        try:
            team_imgs = row.find_elements(By.CSS_SELECTOR, "img[alt]") if row else []
            for img in team_imgs:
                alt_text = img.get_attribute("alt")
                if alt_text and alt_text not in team_names:
                    team_names.append(alt_text)
        except Exception:
            pass

        if len(team_names) < 2:
            try:
                name_elements = row.find_elements(
                    By.CSS_SELECTOR,
                    "span[class*='team'], div[class*='team'], "
                    "span[class*='participant'], div[class*='participant']",
                )
                for elem in name_elements:
                    text = elem.text.strip()
                    if text and self._looks_like_label(text) and not self._looks_like_value(text):
                        if text not in team_names:
                            team_names.append(text)
            except Exception:
                pass

        if len(team_names) >= 2:
            info["home_team"] = team_names[0]
            info["away_team"] = team_names[1]

        # Date/time
        try:
            date_elements = row.find_elements(
                By.CSS_SELECTOR, "time, [class*='date'], [class*='time']"
            )
            date_text = None
            time_text = None
            datetime_attr = None
            for elem in date_elements:
                if not datetime_attr:
                    try:
                        dt_attr = elem.get_attribute("datetime")
                        if dt_attr and "T" in dt_attr:
                            datetime_attr = dt_attr
                    except Exception:
                        pass

                text = elem.text.strip()
                if not text:
                    continue
                if not time_text and self._looks_like_time(text):
                    time_text = text
                if not date_text and self._looks_like_date(text):
                    date_text = text

            if datetime_attr:
                info["datetime"] = datetime_attr
            if date_text:
                info["date"] = date_text
            if time_text:
                info["time"] = time_text
        except Exception:
            pass

        # Tournament/competition
        try:
            tournament_elements = row.find_elements(
                By.CSS_SELECTOR,
                "[class*='tournament'], [class*='league'], [class*='competition']",
            )
            for elem in tournament_elements:
                text = elem.text.strip()
                if text:
                    info["tournament"] = text
                    break
        except Exception:
            pass

        # Status (FT/HT/etc.)
        try:
            status_elements = row.find_elements(
                By.CSS_SELECTOR, "[class*='status'], [class*='period']"
            )
            for elem in status_elements:
                text = elem.text.strip()
                if text:
                    info["status"] = text
                    break
        except Exception:
            pass

        return info

    def is_match_played(self, match_element, listing_info: Dict) -> bool:
        row = self._get_match_row_element(match_element)

        # Explicit finished indicators
        try:
            finished_badges = row.find_elements(
                By.CSS_SELECTOR,
                "[title='TR'], [title='FT'], [title='Terminado'], [title='Finished']",
            )
            if finished_badges:
                return True
        except Exception:
            pass

        # If score exists, it's most likely played
        if listing_info.get("home_score") and listing_info.get("away_score"):
            return True

        status_text = str(listing_info.get("status", "")).lower()
        if status_text in {"ft", "tr", "aet", "pen", "fim", "finished", "terminado"}:
            return True

        return False

    def _extract_score_from_row(self, row) -> Optional[Dict[str, str]]:
        if not row:
            return None

        selectors = [
            ("[data-testid='event-home-score']", "[data-testid='event-away-score']"),
            ("[data-testid='home-score']", "[data-testid='away-score']"),
            ("span[class*='homeScore']", "span[class*='awayScore']"),
            ("div[class*='homeScore']", "div[class*='awayScore']"),
        ]

        for home_sel, away_sel in selectors:
            try:
                home_el = row.find_element(By.CSS_SELECTOR, home_sel)
                away_el = row.find_element(By.CSS_SELECTOR, away_sel)
                home = home_el.text.strip()
                away = away_el.text.strip()
                if home and away:
                    return {"home_score": home, "away_score": away}
            except Exception:
                continue

        return None

    def _extract_score_from_text(self, text: str) -> Optional[Dict[str, str]]:
        if not text:
            return None
        match = re.search(r"(\d+)\s*[-:]\s*(\d+)", text)
        if match:
            return {"home_score": match.group(1), "away_score": match.group(2)}
        return None

    def _get_match_row_element(self, match_element):
        row_xpaths = [
            "./ancestor::*[self::div or self::li][contains(@class,'event')][1]",
            "./ancestor::*[self::div or self::li][contains(@class,'match')][1]",
            "./ancestor::*[self::div or self::li][contains(@class,'row')][1]",
            "./ancestor::*[self::div or self::li][1]",
        ]
        for xpath in row_xpaths:
            try:
                return match_element.find_element(By.XPATH, xpath)
            except Exception:
                continue
        return match_element

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

    def _looks_like_time(self, text: str) -> bool:
        if not text:
            return False
        return bool(re.search(r"\b\d{1,2}:\d{2}\b", text)) or bool(
            re.search(r"\b\d{1,2}h\d{2}\b", text)
        )

    def _looks_like_date(self, text: str) -> bool:
        if not text:
            return False
        lowered = text.strip().lower()
        if lowered in {"hoje", "amanha", "amanhã", "ontem"}:
            return True
        if re.search(r"\b\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?\b", lowered):
            return True
        months = {
            "jan",
            "fev",
            "mar",
            "abr",
            "mai",
            "jun",
            "jul",
            "ago",
            "set",
            "out",
            "nov",
            "dez",
        }
        return any(m in lowered for m in months)
