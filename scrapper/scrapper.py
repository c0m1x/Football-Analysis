"""
Gil Vicente FC SofaScore Next Opponent Statistics Scraper
This script:
1. Goes to Gil Vicente's page
2. Finds their NEXT game
3. Identifies the opponent
4. Goes to opponent's page
5. Scrapes last 10 matches statistics (individual + aggregated)
"""

import os
import sys
from pathlib import Path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
import re

from listing_extractor import ListingExtractor
from stats_extractor import MatchStatsExtractor


class SofaScoreScraper:
    """
    Scraper for collecting next opponent's last 10 matches statistics.
    """
    
    def __init__(self, headless: bool = False):
        """
        Initialize the scraper with Selenium WebDriver.
        
        Args:
            headless: Run browser in headless mode (default: False for debugging)
        """
        print("Initializing browser...")
        
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--start-maximized')
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        chrome_options.add_argument(f"user-agent={self.user_agent}")

        # Enable performance logs so we can capture match statistics JSON via CDP when DOM parsing fails.
        chrome_options.set_capability(
            "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
        )
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 15)

        # Make CDP Network APIs available (best-effort).
        try:
            self.driver.execute_cdp_cmd("Network.enable", {})
        except Exception:
            pass
        
        self.team_url = "https://www.sofascore.com/pt-pt/football/team/gil-vicente/3010"
        self.stats_extractor = MatchStatsExtractor(self.driver, user_agent=self.user_agent)
        self.listing_extractor = ListingExtractor(self.driver)
        
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            print("Browser closed.")
    
    
    def find_next_match(self) -> Optional[Dict]:
        """
        Find Gil Vicente's next upcoming match.
        
        Returns:
            Dictionary with next match info or None
        """
        print("\n" + "="*80)
        print("STEP 1: Finding Gil Vicente's Next Match")
        print("="*80)
        
        try:
            # Wait for page to load completely
            time.sleep(4)
            
            # Try to find the next match link using the structure you provided
            # Looking for: a[href*="/football/match/"] with specific classes
            print("  → Looking for next match in fixtures...")
            
            # Multiple strategies to find the next match
            next_match_element = None
            
            # Strategy 1: Find by event link with specific pattern
            try:
                match_links = self.driver.find_elements(By.CSS_SELECTOR, 
                    "a[href*='/football/match/']")
                
                if match_links:
                    print(f"  → Found {len(match_links)} match links")
                    # Get the second one (should be the next match)
                    next_match_element = match_links[1]
                    print(f"  → Selected second match: {next_match_element.get_attribute('href')}")
            except Exception as e:
                print(f"  → Strategy 1 failed: {e}")
            
            # Strategy 2: Find by data-id attribute (event ID)
            if not next_match_element:
                try:
                    match_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        "a[data-id]")
                    
                    for elem in match_elements:
                        href = elem.get_attribute('href')
                        if href and '/football/match/' in href:
                            next_match_element = elem
                            print(f"  → Found match via data-id: {href}")
                            break
                except Exception as e:
                    print(f"  → Strategy 2 failed: {e}")
            
            # Strategy 3: Find by class pattern you mentioned
            if not next_match_element:
                try:
                    match_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        "a.d_block[href*='/match/']")
                    
                    if match_elements:
                        next_match_element = match_elements[0]
                        print(f"  → Found match via class pattern")
                except Exception as e:
                    print(f"  → Strategy 3 failed: {e}")
            
            if not next_match_element:
                print("  WARNING: Could not find next match with any strategy")
                # Debug: print page source snippet
                print("\n  DEBUG: Searching for match patterns in page...")
                try:
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    print(f"  Total links on page: {len(all_links)}")
                    match_count = 0
                    for link in all_links[:50]:  # Check first 50 links
                        href = link.get_attribute('href')
                        if href and 'match' in href:
                            print(f"    - {href}")
                            match_count += 1
                    print(f"  Found {match_count} potential match links")
                except:
                    pass
                return None
            
            # Click on the next match
            print("  → Scrolling to match element...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_match_element)
            time.sleep(1)
            
            print("  → Clicking on match...")
            try:
                next_match_element.click()
            except:
                # Try JavaScript click if regular click fails
                print("  → Regular click failed, trying JavaScript click...")
                self.driver.execute_script("arguments[0].click();", next_match_element)
            
            time.sleep(4)
            
            # Extract match information from the match page
            match_info = {}
            
            print("  → Extracting match details...")
            
            # Get teams using the structure from your HTML
            # Looking for team names in the format you showed
            teams = self.driver.find_elements(By.CSS_SELECTOR, 
                "a[class*='participant'], bdi.trunc_true")
            
            team_names = []
            for team in teams:
                text = team.text.strip()
                if text and len(text) > 2:  # Filter out empty or very short text
                    team_names.append(text)
                    if len(team_names) == 2:
                        break
            
            # Alternative: try to find team names in img alt attributes
            if len(team_names) < 2:
                team_imgs = self.driver.find_elements(By.CSS_SELECTOR, "img[alt]")
                team_names = []
                for img in team_imgs:
                    alt_text = img.get_attribute('alt')
                    if alt_text and len(alt_text) > 2 and alt_text not in team_names:
                        team_names.append(alt_text)
                        if len(team_names) == 2:
                            break
            
            if len(team_names) >= 2:
                match_info['home_team'] = team_names[0]
                match_info['away_team'] = team_names[1]
                
                # Determine opponent
                gil_vicente_variations = ['gil vicente', 'gilvicente']
                
                home_is_gil = any(gv in match_info['home_team'].lower() 
                                for gv in gil_vicente_variations)
                away_is_gil = any(gv in match_info['away_team'].lower() 
                                for gv in gil_vicente_variations)
                
                if home_is_gil:
                    match_info['opponent'] = match_info['away_team']
                    match_info['opponent_position'] = 'away'
                    match_info['gil_vicente_home'] = True
                elif away_is_gil:
                    match_info['opponent'] = match_info['home_team']
                    match_info['opponent_position'] = 'home'
                    match_info['gil_vicente_home'] = False
                else:
                    print(f"  WARNING: Could not identify Gil Vicente in teams: {team_names}")
                    return None
                
                print("\nNext Match Found:")
                print(f"  {match_info['home_team']} vs {match_info['away_team']}")
                print(f"  Opponent: {match_info['opponent']}")
                print(f"  Gil Vicente: {'Home' if match_info['gil_vicente_home'] else 'Away'}")
                
                match_info['match_url'] = self.driver.current_url
                return match_info
            else:
                print(f"  WARNING: Could not extract team names (found {len(team_names)})")
                return None
            
        except Exception as e:
            print(f"  WARNING: Error finding next match: {e}")
            import traceback
            traceback.print_exc()
        
        return None

    def scrape_gil_vicente_fixtures(self, limit: int = 30) -> pd.DataFrame:
        """Scrape Gil Vicente fixtures list from the team page."""
        print("\n" + "=" * 80)
        print("STEP 0: Capturing Gil Vicente fixtures (offline cache)")
        print("=" * 80)

        fixtures = []
        try:
            time.sleep(2)
            match_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "a[href*='/football/match/']"
            )
            print(f"  Found {len(match_elements)} match links on team page")

            seen_urls = set()
            gil_variations = ["gil vicente", "gilvicente"]

            for elem in match_elements:
                if len(fixtures) >= limit:
                    break

                try:
                    url = elem.get_attribute("href")
                    if not url or url in seen_urls:
                        continue

                    listing_info = self.listing_extractor.extract_basic_info_from_listing(elem)
                    home = listing_info.get("home_team")
                    away = listing_info.get("away_team")
                    if not home or not away:
                        continue

                    home_is_gil = any(gv in home.lower() for gv in gil_variations)
                    away_is_gil = any(gv in away.lower() for gv in gil_variations)
                    if not home_is_gil and not away_is_gil:
                        continue

                    is_home = bool(home_is_gil)
                    opponent = away if is_home else home

                    status = "finished" if self.listing_extractor.is_match_played(elem, listing_info) else "upcoming"
                    match_id = None
                    match_id_match = re.search(r"#id:(\d+)", url)
                    if match_id_match:
                        match_id = match_id_match.group(1)

                    fixtures.append(
                        {
                            "match_id": match_id,
                            "match_url": url,
                            "home_team": home,
                            "away_team": away,
                            "home_score": listing_info.get("home_score"),
                            "away_score": listing_info.get("away_score"),
                            "date": listing_info.get("date"),
                            "time": listing_info.get("time"),
                            "datetime": listing_info.get("datetime"),
                            "tournament": listing_info.get("tournament"),
                            "status": status,
                            "gil_vicente_home": is_home,
                            "opponent_name": opponent,
                        }
                    )

                    seen_urls.add(url)
                except Exception:
                    continue

            print(f"  Captured {len(fixtures)} fixtures")
        except Exception as e:
            print(f"  WARNING: Error scraping fixtures: {e}")

        return pd.DataFrame(fixtures)
    
    def navigate_to_opponent_page(self, opponent_position: str) -> bool:
        """
        Navigate to opponent's team page from match page.
        
        Args:
            opponent_position: 'home' or 'away'
            
        Returns:
            True if successful
        """
        print("\n" + "="*80)
        print("STEP 2: Navigating to Opponent's Page")
        print("="*80)
        
        try:
            time.sleep(2)
            
            # Strategy 1: Find team links by looking at the team images/names
            team_containers = self.driver.find_elements(By.CSS_SELECTOR, 
                "div[class*='participant'], a[class*='participant']")
            
            opponent_link = None
            
            # The structure usually has home team first, away team second
            if opponent_position == 'home' and len(team_containers) >= 1:
                opponent_link = team_containers[0]
            elif opponent_position == 'away' and len(team_containers) >= 2:
                opponent_link = team_containers[1]
            
            # Strategy 2: Try finding by team images
            if not opponent_link:
                team_imgs = self.driver.find_elements(By.CSS_SELECTOR, "img[alt]")
                
                for i, img in enumerate(team_imgs):
                    alt_text = img.get_attribute('alt')
                    if alt_text and 'gil vicente' not in alt_text.lower():
                        # Found opponent, try to get clickable parent
                        try:
                            opponent_link = img.find_element(By.XPATH, "./ancestor::a")
                            if opponent_link:
                                break
                        except:
                            continue
            
            if not opponent_link:
                print("  WARNING: Could not find opponent link")
                # Debug
                print("\n  DEBUG: Available team elements:")
                for i, container in enumerate(team_containers[:5]):
                    print(f"    {i}: {container.text[:100] if container.text else 'No text'}")
                return False
            
            opponent_name = opponent_link.text.strip() if opponent_link.text else "Opponent"
            print(f"  → Clicking on {opponent_name}...")
            
            # Scroll to element
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", 
                                     opponent_link)
            time.sleep(0.5)
            
            # Try to click
            try:
                opponent_link.click()
            except:
                # Try JavaScript click
                print("  → Trying JavaScript click...")
                self.driver.execute_script("arguments[0].click();", opponent_link)
            
            time.sleep(4)
            
            print(f"  OK: Successfully navigated to {opponent_name}'s page")
            print(f"  URL: {self.driver.current_url}")
            return True
            
        except Exception as e:
            print(f"  WARNING: Error navigating to opponent page: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    
    def get_match_basic_info(self) -> Dict:
        """Extract basic match information."""
        info = {}
        
        try:
            # Get teams
            home_team = None
            away_team = None

            try:
                home_el = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='home-team-name']")
                away_el = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='away-team-name']")
                home_team = home_el.text.strip()
                away_team = away_el.text.strip()
            except Exception:
                pass

            if not home_team or not away_team:
                team_selectors = [
                    "a[class*='participant']",
                    "div[class*='participant']",
                    "span[class*='participant']",
                    "a[class*='team']",
                    "div[class*='team']",
                    "span[class*='team']",
                ]
                team_names = []
                for selector in team_selectors:
                    try:
                        teams = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for team in teams:
                            text = team.text.strip()
                            if text and text not in team_names:
                                team_names.append(text)
                            if len(team_names) >= 2:
                                break
                    except Exception:
                        continue
                    if len(team_names) >= 2:
                        break

                if len(team_names) >= 2:
                    home_team = home_team or team_names[0]
                    away_team = away_team or team_names[1]

            if home_team and away_team:
                info['home_team'] = home_team
                info['away_team'] = away_team
            
            # Get score
            home_score = None
            away_score = None
            try:
                home_score_el = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='home-score']")
                away_score_el = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='away-score']")
                home_score = home_score_el.text.strip()
                away_score = away_score_el.text.strip()
            except Exception:
                pass

            if not home_score or not away_score:
                scores = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[class*='detailScore'], span[class*='detailScore']"
                )
                if len(scores) >= 2:
                    home_score = scores[0].text.strip()
                    away_score = scores[1].text.strip()

            if not home_score or not away_score:
                score_container = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "div[class*='score'], span[class*='score'], "
                    "[data-testid='match-score'], [data-testid='score']",
                )
                for elem in score_container:
                    text = elem.text.strip()
                    match = re.search(r'(\d+)\s*[-:]\s*(\d+)', text)
                    if match:
                        home_score = match.group(1)
                        away_score = match.group(2)
                        break

            if home_score is not None and away_score is not None:
                info['home_score'] = home_score
                info['away_score'] = away_score
            
            # Get date
            date_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                "div[class*='startTime'], div[class*='date'], span[class*='date'], "
                "time, [data-testid='match-starttime']")
            if date_elements:
                info['date'] = date_elements[0].text.strip()
            
            # Get tournament
            tournament_elements = self.driver.find_elements(By.CSS_SELECTOR,
                "a[class*='tournament'], div[class*='tournament'], "
                "a[class*='league'], div[class*='league']")
            if tournament_elements:
                info['tournament'] = tournament_elements[0].text.strip()
                
        except Exception as e:
            print(f"      WARNING: Error getting basic info: {e}")
        
        return info
    
    def scrape_opponent_last_10_matches(self, opponent_name: str) -> pd.DataFrame:
        """
        Scrape the last matches from opponent's page.

        Behaviour changed:
            - Only consider sidebar matches from 3rd to 10th item (indices 2..9)
            - Only click/process matches that are already played (div[title='TR'])
        """
        print("\n" + "="*80)
        print(f"STEP 3: Scraping {opponent_name}'s Last Matches (sidebar 3..10, played only)")
        print("="*80)

        all_matches = []

        try:
            # Wait for page to load
            time.sleep(3)

            # Find sidebar container and scroll it to ensure items are loaded
            print("\n  → Looking for matches in sidebar...")
            sidebar = None
            try:
                sidebar_candidates = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[class*='sidebar'], div[class*='events'], div[class*='sidebar__container']"
                )
                if sidebar_candidates:
                    sidebar = sidebar_candidates[0]
                    # Try to scroll to bottom to load all events
                    try:
                        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", sidebar)
                        time.sleep(1)
                    except:
                        pass
            except:
                sidebar = None

            print("\n  → Looking for played matches on opponent page...")

            match_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "a[href*='/football/match/']"
            )

            print(f"  Found {len(match_elements)} match links")

            match_candidates = []
            seen_urls = set()
            MAX_MATCHES = 8  # ou 10 se quiseres mesmo 10

            for idx, elem in enumerate(match_elements):
                # ignorar os dois primeiros (jogos futuros)
                if idx < 2:
                    continue

                if len(match_candidates) >= MAX_MATCHES:
                    break

                try:
                    url = elem.get_attribute("href")
                    if not url or url in seen_urls:
                        continue

                    listing_info = self.listing_extractor.extract_basic_info_from_listing(elem)
                    if not self.listing_extractor.is_match_played(elem, listing_info):
                        continue

                    seen_urls.add(url)
                    match_candidates.append({
                        'url': url,
                        'listing_info': listing_info,
                    })

                    print(f"    + Added match {len(match_candidates)} -> index {idx+1}")

                except Exception:
                    continue

            print(f"\n  Will process {len(match_candidates)} matches")


            # Scrape each selected match (preserve ordering)
            for idx, match_item in enumerate(match_candidates, 1):
                match_url = match_item['url']
                listing_info = match_item.get('listing_info', {})
                print(f"\n  [{idx}/{len(match_candidates)}] Processing match {match_url} ...")

                try:
                    # Clear performance logs so CDP capture works per-match.
                    try:
                        self.driver.get_log("performance")
                    except Exception:
                        pass

                    # Navigate to match
                    match_url_to_open = match_url
                    if "#id:" in match_url_to_open and "tab:statistics" not in match_url_to_open:
                        match_url_to_open = f"{match_url_to_open},tab:statistics"

                    self.driver.get(match_url_to_open)
                    time.sleep(3)

                    # Get basic info
                    match_data = dict(listing_info) if listing_info else {}
                    match_page_info = self.get_match_basic_info()
                    for key, value in match_page_info.items():
                        if value:
                            match_data[key] = value
                    match_data['match_number'] = idx
                    match_data['match_url'] = match_url

                    print(f"    Match: {match_data.get('home_team', '?')} vs {match_data.get('away_team', '?')}")
                    print(f"    Score: {match_data.get('home_score', '?')} - {match_data.get('away_score', '?')}")

                    # Extract statistics
                    stats = self.stats_extractor.extract_match_statistics(idx, match_url)
                    if stats:
                        match_data.update(stats)

                    all_matches.append(match_data)

                except Exception as e:
                    print(f"    WARNING: Error processing match {idx}: {e}")
                    continue

                # Small delay between matches
                time.sleep(1)

            print(f"\n  Successfully scraped {len(all_matches)} matches")

        except Exception as e:
            print(f"  WARNING: Error scraping matches: {e}")
            import traceback
            traceback.print_exc()

        return pd.DataFrame(all_matches)
    
    def calculate_aggregated_statistics(self, df: pd.DataFrame, opponent_name: str) -> Dict:
        """
        Calculate aggregated statistics from last 10 matches.
        
        Args:
            df: DataFrame with individual match statistics
            opponent_name: Name of the opponent
            
        Returns:
            Dictionary with aggregated statistics
        """
        print("\n" + "="*80)
        print(f"STEP 4: Calculating Aggregated Statistics for {opponent_name}")
        print("="*80)
        
        aggregated = {
            'opponent_name': opponent_name,
            'total_matches_analyzed': len(df),
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if df.empty:
            print("  WARNING: No data to aggregate")
            return aggregated
        
        try:
            # Identify numeric columns (statistics)
            stat_columns = [col for col in df.columns 
                          if ('_home' in col or '_away' in col) 
                          and col not in ['home_team', 'away_team', 'home_score', 'away_score']]
            
            print(f"\n  Aggregating {len(stat_columns)} statistical metrics...")
            
            # Calculate wins/draws/losses
            if 'home_score' in df.columns and 'away_score' in df.columns:
                try:
                    # Determine if opponent was home or away and calculate results
                    df['opponent_goals'] = df.apply(
                        lambda row: row.get('home_score', 0) 
                        if opponent_name.lower() in str(row.get('home_team', '')).lower()
                        else row.get('away_score', 0),
                        axis=1
                    )
                    
                    df['opponent_goals_conceded'] = df.apply(
                        lambda row: row.get('away_score', 0)
                        if opponent_name.lower() in str(row.get('home_team', '')).lower()
                        else row.get('home_score', 0),
                        axis=1
                    )
                    
                    # Convert to numeric
                    df['opponent_goals'] = pd.to_numeric(df['opponent_goals'], errors='coerce').fillna(0)
                    df['opponent_goals_conceded'] = pd.to_numeric(df['opponent_goals_conceded'], errors='coerce').fillna(0)
                    
                    aggregated['total_goals_scored'] = int(df['opponent_goals'].sum())
                    aggregated['total_goals_conceded'] = int(df['opponent_goals_conceded'].sum())
                    aggregated['avg_goals_scored'] = round(df['opponent_goals'].mean(), 2)
                    aggregated['avg_goals_conceded'] = round(df['opponent_goals_conceded'].mean(), 2)
                    
                    # Calculate wins/draws/losses
                    df['result'] = df.apply(
                        lambda row: 'W' if row['opponent_goals'] > row['opponent_goals_conceded']
                        else ('D' if row['opponent_goals'] == row['opponent_goals_conceded'] else 'L'),
                        axis=1
                    )
                    
                    aggregated['wins'] = int((df['result'] == 'W').sum())
                    aggregated['draws'] = int((df['result'] == 'D').sum())
                    aggregated['losses'] = int((df['result'] == 'L').sum())
                    aggregated['win_percentage'] = round((aggregated['wins'] / len(df)) * 100, 2)
                    
                except Exception as e:
                    print(f"    WARNING: Error calculating match results: {e}")
            
            # Aggregate other statistics
            for col in stat_columns:
                try:
                    # Try to extract numeric values from the column
                    numeric_series = df[col].apply(self._extract_numeric_value)
                    
                    # Remove NaN values
                    numeric_series = numeric_series.dropna()
                    
                    if len(numeric_series) > 0:
                        # Calculate aggregates
                        col_name = col.replace('_home', '').replace('_away', '')
                        
                        aggregated[f'{col_name}_total'] = round(numeric_series.sum(), 2)
                        aggregated[f'{col_name}_avg'] = round(numeric_series.mean(), 2)
                        aggregated[f'{col_name}_max'] = round(numeric_series.max(), 2)
                        aggregated[f'{col_name}_min'] = round(numeric_series.min(), 2)
                        
                except Exception as e:
                    continue
            
            print("  Aggregated statistics calculated")
            print(f"\n  Key Metrics:")
            print(f"    Record: {aggregated.get('wins', 0)}W - {aggregated.get('draws', 0)}D - {aggregated.get('losses', 0)}L")
            print(f"    Goals: {aggregated.get('total_goals_scored', 0)} scored, {aggregated.get('total_goals_conceded', 0)} conceded")
            print(f"    Avg Goals/Game: {aggregated.get('avg_goals_scored', 0)}")
            
        except Exception as e:
            print(f"  WARNING: Error calculating aggregated stats: {e}")
            import traceback
            traceback.print_exc()
        
        return aggregated
    
    def _extract_numeric_value(self, value) -> float:
        """Extract numeric value from string."""
        if pd.isna(value):
            return None
        
        try:
            # Convert to string
            value_str = str(value)
            
            # Remove percentage signs and other non-numeric characters except dots and minus
            value_str = re.sub(r'[^\d.\-]', '', value_str)
            
            if value_str and value_str != '-':
                return float(value_str)
        except:
            pass
        
        return None
    
    def run_complete_analysis(self):
        """
        Run the complete scraping workflow.
        
        Returns:
            Tuple of (individual_matches_df, aggregated_stats_dict, fixtures_df)
        """
        print("\n" + "="*80)
        print("GIL VICENTE FC - NEXT OPPONENT ANALYSIS")
        print("="*80)
        print("\nWorkflow:")
        print("0. Capture fixtures for offline cache")
        print("1. Find Gil Vicente's next match")
        print("2. Navigate to opponent's page")
        print("3. Scrape opponent's last 10 matches")
        print("4. Calculate aggregated statistics")
        print("="*80)
        
        try:
            # Navigate to Gil Vicente's page
            print(f"\nNavigating to: {self.team_url}")
            self.driver.get(self.team_url)
            time.sleep(3)
            
            
            # Step 0: Capture fixtures for offline cache
            fixtures_df = self.scrape_gil_vicente_fixtures()

            # Step 1: Find next match
            match_info = self.find_next_match()
            
            if not match_info:
                print("\nWARNING: Could not find next match. Exiting...")
                return None, None, fixtures_df
            
            opponent_name = match_info['opponent']
            
            # Step 2: Navigate to opponent's page
            if not self.navigate_to_opponent_page(match_info['opponent_position']):
                print("\nWARNING: Could not navigate to opponent's page. Exiting...")
                return None, None, fixtures_df
            
            # Step 3: Scrape opponent's last 10 matches
            individual_matches_df = self.scrape_opponent_last_10_matches(opponent_name)
            
            if individual_matches_df.empty:
                print("\nWARNING: No matches were scraped. Exiting...")
                return None, None, fixtures_df
            
            # Step 4: Calculate aggregated statistics
            aggregated_stats = self.calculate_aggregated_statistics(
                individual_matches_df, 
                opponent_name
            )
            
            return individual_matches_df, aggregated_stats, fixtures_df
            
        except Exception as e:
            print(f"\nWARNING: Error in complete analysis: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None
    
    
    def save_results(
        self,
        individual_df: Optional[pd.DataFrame],
        aggregated_dict: Optional[Dict],
        fixtures_df: Optional[pd.DataFrame] = None,
    ):
        """Save results to files."""
        print("\n" + "="*80)
        print("STEP 5: Saving Results")
        print("="*80)

        export_dir_env = (os.getenv("SCRAPER_EXPORT_DIR") or "").strip()
        if export_dir_env:
            export_dir = Path(export_dir_env).expanduser()
        else:
            repo_root = Path(__file__).resolve().parents[1]
            export_dir = repo_root / "data" / "scraper_exports"

        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        opponent = (
            aggregated_dict.get('opponent_name', 'opponent').replace(' ', '_')
            if aggregated_dict
            else 'opponent'
        )

        if individual_df is not None and aggregated_dict is not None:
            # Save individual matches
            individual_csv = f"gil_vicente_next_opponent_{opponent}_individual_{timestamp}.csv"
            individual_csv_path = export_dir / individual_csv
            individual_df.to_csv(str(individual_csv_path), index=False, encoding='utf-8')
            print(f"\n  Individual matches saved to: {individual_csv_path}")

            individual_json = f"gil_vicente_next_opponent_{opponent}_individual_{timestamp}.json"
            individual_json_path = export_dir / individual_json
            individual_df.to_json(str(individual_json_path), orient='records', indent=2, force_ascii=False)
            print(f"  Individual matches saved to: {individual_json_path}")

            # Save aggregated statistics
            aggregated_df = pd.DataFrame([aggregated_dict])
            aggregated_csv = f"gil_vicente_next_opponent_{opponent}_aggregated_{timestamp}.csv"
            aggregated_csv_path = export_dir / aggregated_csv
            aggregated_df.to_csv(str(aggregated_csv_path), index=False, encoding='utf-8')
            print(f"\n  Aggregated stats saved to: {aggregated_csv_path}")

            aggregated_json = f"gil_vicente_next_opponent_{opponent}_aggregated_{timestamp}.json"
            aggregated_json_path = export_dir / aggregated_json
            aggregated_df.to_json(str(aggregated_json_path), orient='records', indent=2, force_ascii=False)
            print(f"  Aggregated stats saved to: {aggregated_json_path}")

        # Save fixtures cache (offline mode)
        if fixtures_df is not None and not fixtures_df.empty:
            fixtures_csv = f"gil_vicente_fixtures_{timestamp}.csv"
            fixtures_csv_path = export_dir / fixtures_csv
            fixtures_df.to_csv(str(fixtures_csv_path), index=False, encoding="utf-8")
            print(f"\n  Fixtures cache saved to: {fixtures_csv_path}")

            fixtures_json = f"gil_vicente_fixtures_{timestamp}.json"
            fixtures_json_path = export_dir / fixtures_json
            fixtures_df.to_json(str(fixtures_json_path), orient="records", indent=2, force_ascii=False)
            print(f"  Fixtures cache saved to: {fixtures_json_path}")
        
        # Print summary
        if aggregated_dict is not None and individual_df is not None:
            print("\n" + "="*80)
            print("FINAL SUMMARY")
            print("="*80)
            print(f"\nOpponent: {aggregated_dict.get('opponent_name', 'N/A')}")
            print(f"Matches Analyzed: {aggregated_dict.get('total_matches_analyzed', 0)}")
            print(
                f"\nLast 8 Games Record: {aggregated_dict.get('wins', 0)}W - "
                f"{aggregated_dict.get('draws', 0)}D - {aggregated_dict.get('losses', 0)}L"
            )
            print(f"Win Rate: {aggregated_dict.get('win_percentage', 0)}%")
            print(
                f"Goals Scored: {aggregated_dict.get('total_goals_scored', 0)} "
                f"(Avg: {aggregated_dict.get('avg_goals_scored', 0)}/game)"
            )
            print(
                f"Goals Conceded: {aggregated_dict.get('total_goals_conceded', 0)} "
                f"(Avg: {aggregated_dict.get('avg_goals_conceded', 0)}/game)"
            )
            print(f"\nTotal Statistics Collected: {len(individual_df.columns)} metrics per match")
            print(f"Total Aggregated Metrics: {len(aggregated_dict)} calculated values")


def main():
    """Main execution function."""
    scraper = None
    
    try:
        # Initialize scraper
        scraper = SofaScoreScraper(headless=False)
        
        # Run complete analysis
        individual_df, aggregated_stats, fixtures_df = scraper.run_complete_analysis()
        
        if (individual_df is not None and aggregated_stats is not None) or (
            fixtures_df is not None and not fixtures_df.empty
        ):
            # Save results
            scraper.save_results(individual_df, aggregated_stats, fixtures_df)

            print("\n" + "="*80)
            print("ANALYSIS COMPLETE!")
            print("="*80)
        else:
            print("\nWARNING: Analysis could not be completed. Check errors above.")
    
    except KeyboardInterrupt:
        print("\n\nWARNING: Scraping interrupted by user.")
    except Exception as e:
        print(f"\nWARNING: An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if scraper:
            print("\nClosing browser...")
            scraper.close()


if __name__ == "__main__":
    main()
