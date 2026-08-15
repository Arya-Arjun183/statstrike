import os
import requests
from dotenv import load_dotenv
from premier_league_predictor.api_football import fetch_api, LEAGUE_ID
from premier_league_predictor.data import normalize_team_name
from functools import lru_cache

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")

@lru_cache(maxsize=1)
def _fetch_all_odds():
    if not ODDS_API_KEY:
        return []
        
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={ODDS_API_KEY}&regions=uk&markets=h2h&bookmakers=pinnacle,bet365"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching odds: {e}")
        return []

def get_match_odds(home_team: str, away_team: str) -> dict:
    """
    Fetch 1X2 moneyline odds from The-Odds-API and calculate implied probabilities.
    Returns a dict with home_win, draw, away_win (implied probabilities and raw decimal odds).
    """
    data = _fetch_all_odds()
    if not data:
        return None
        
    try:
        
        home_norm = normalize_team_name(home_team)
        away_norm = normalize_team_name(away_team)
        
        for match in data:
            h_api = normalize_team_name(match.get("home_team", ""))
            a_api = normalize_team_name(match.get("away_team", ""))
            
            if h_api == home_norm and a_api == away_norm:
                bookies = match.get("bookmakers", [])
                if not bookies:
                    continue
                # Get the first available bookmaker's odds
                market = bookies[0]["markets"][0]
                outcomes = market["outcomes"]
                
                odds_dict = {}
                for oc in outcomes:
                    oc_norm = normalize_team_name(oc["name"])
                    if oc_norm == home_norm:
                        odds_dict["home"] = oc["price"]
                    elif oc_norm == away_norm:
                        odds_dict["away"] = oc["price"]
                    elif oc["name"].lower() == "draw":
                        odds_dict["draw"] = oc["price"]
                        
                if "home" in odds_dict and "draw" in odds_dict and "away" in odds_dict:
                    # Calculate implied probabilities (with overround removal)
                    raw_p_home = 1 / odds_dict["home"]
                    raw_p_draw = 1 / odds_dict["draw"]
                    raw_p_away = 1 / odds_dict["away"]
                    overround = raw_p_home + raw_p_draw + raw_p_away
                    
                    return {
                        "home_odds": odds_dict["home"],
                        "draw_odds": odds_dict["draw"],
                        "away_odds": odds_dict["away"],
                        "home_implied": round(raw_p_home / overround, 3),
                        "draw_implied": round(raw_p_draw / overround, 3),
                        "away_implied": round(raw_p_away / overround, 3),
                    }
                    
        return None
    except Exception as e:
        print(f"Error fetching odds: {e}")
        return None


