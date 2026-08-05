import os
import json
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_HOST = os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io")

LEAGUE_ID = 39 # Premier League

from premier_league_predictor.data import normalize_team_name

TEAM_NAME_MAPPING = {
    "Manchester United": "Manchester United",
    "Manchester City": "Manchester City",
    "Nottingham Forest": "Nottingham Forest",
    "Tottenham": "Tottenham",
    "Tottenham Hotspur": "Tottenham",
    "Wolverhampton": "Wolverhampton Wanderers",
    "Wolverhampton Wanderers": "Wolverhampton Wanderers",
    "Sheffield Utd": "Sheffield United",
    "Brighton": "Brighton",
    "Brighton & Hove Albion": "Brighton",
    "Aston Villa": "Aston Villa",
    "Leicester": "Leicester",
    "Leicester City": "Leicester",
    "Leeds": "Leeds",
    "Leeds United": "Leeds",
    "West Ham": "West Ham",
    "West Ham United": "West Ham",
    "Everton": "Everton",
    "Chelsea": "Chelsea",
    "Arsenal": "Arsenal",
    "Liverpool": "Liverpool",
    "Newcastle": "Newcastle United",
    "Newcastle United": "Newcastle United",
    "Crystal Palace": "Crystal Palace",
    "Bournemouth": "Bournemouth",
    "Fulham": "Fulham",
    "Brentford": "Brentford",
    "Ipswich": "Ipswich",
    "Ipswich Town": "Ipswich",
    "Southampton": "Southampton",
    "Burnley": "Burnley",
    "Luton": "Luton",
    "Luton Town": "Luton",
}

def get_mapped_team_name(api_name: str) -> str:
    mapped = TEAM_NAME_MAPPING.get(api_name, api_name)
    return normalize_team_name(mapped)

def fetch_api(endpoint: str, params: dict = None) -> dict:
    if not API_FOOTBALL_KEY:
        print("API_FOOTBALL_KEY not found in environment, skipping API-Football sync.")
        return {}
    
    url = f"https://{API_FOOTBALL_HOST}/{endpoint}"
    headers = {
        "x-rapidapi-key": API_FOOTBALL_KEY,
        "x-rapidapi-host": API_FOOTBALL_HOST
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def extract_expected_goals(fixture_id: int) -> tuple[float, float]:
    """Fetch statistics for a fixture and extract home and away expected goals."""
    data = fetch_api("fixtures/statistics", {"fixture": fixture_id})
    if not data or "response" not in data or len(data["response"]) < 2:
        return 0.0, 0.0
    
    home_xg = 0.0
    away_xg = 0.0
    
    try:
        home_stats = data["response"][0]["statistics"]
        away_stats = data["response"][1]["statistics"]
        
        for stat in home_stats:
            if stat["type"] == "expected_goals":
                home_xg = float(stat["value"]) if stat["value"] is not None else 0.0
                break
                
        for stat in away_stats:
            if stat["type"] == "expected_goals":
                away_xg = float(stat["value"]) if stat["value"] is not None else 0.0
                break
    except Exception as e:
        print(f"Failed to parse xG for fixture {fixture_id}: {e}")
        
    return home_xg, away_xg


def sync_latest_data(season: int = 2024) -> pd.DataFrame:
    """
    Sync latest completed matches from API-Football and return as DataFrame.
    Uses a local cache file to avoid hitting the API repeatedly for old matches.
    """
    cache_path = Path("data/raw/premier/api-football-cache.csv")
    
    if cache_path.exists():
        df_cache = pd.read_csv(cache_path)
    else:
        df_cache = pd.DataFrame(columns=["Date", "HomeTeam", "AwayTeam", "goals_home", "goals_away", "HXG", "AXG", "fixture_id"])
        
    if not API_FOOTBALL_KEY:
        return df_cache

    cached_fixture_ids = set(df_cache["fixture_id"].dropna().astype(int)) if "fixture_id" in df_cache.columns else set()
    
    print("Checking API-Football for new completed fixtures...")
    try:
        fixtures_data = fetch_api("fixtures", {"league": LEAGUE_ID, "season": season, "status": "FT"})
        if not fixtures_data or "response" not in fixtures_data:
            return df_cache
            
        new_rows = []
        for match in fixtures_data["response"]:
            fixture_id = match["fixture"]["id"]
            if fixture_id in cached_fixture_ids:
                continue
                
            date_str = match["fixture"]["date"][:10]
            y, m, d = date_str.split("-")
            date_formatted = f"{d}/{m}/{y}"
            
            home_team = get_mapped_team_name(match["teams"]["home"]["name"])
            away_team = get_mapped_team_name(match["teams"]["away"]["name"])
            
            goals_home = match["goals"]["home"]
            goals_away = match["goals"]["away"]
            
            print(f"Fetching xG for {home_team} vs {away_team}...")
            home_xg, away_xg = extract_expected_goals(fixture_id)
            
            new_rows.append({
                "Date": date_formatted,
                "HomeTeam": home_team,
                "AwayTeam": away_team,
                "goals_home": goals_home,
                "goals_away": goals_away,
                "HXG": home_xg,
                "AXG": away_xg,
                "fixture_id": fixture_id
            })
            
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            df_cache = pd.concat([df_cache, new_df], ignore_index=True)
            df_cache.to_csv(cache_path, index=False)
            print(f"Added {len(new_rows)} new matches to cache.")
        else:
            print("No new completed matches found.")
            
    except Exception as e:
        print(f"API-Football sync failed: {e}")
        
    return df_cache
