from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import poisson

from premier_league_predictor.config import load_config
from premier_league_predictor.data import load_matches, normalize_team_name
from premier_league_predictor.prediction import predict_fixtures
from premier_league_predictor.api_football import fetch_api, LEAGUE_ID, get_mapped_team_name, API_FOOTBALL_KEY
from premier_league_predictor.external_data import get_match_odds

CONFIG_PATH = "configs/test_xg_efficient.yaml"
FIXTURES_FILE_PATH = Path("data/raw/premier/fixtures-26-27.csv")

TEAM_STADIUMS = {
    "Arsenal": "Emirates Stadium",
    "Aston Villa": "Villa Park",
    "Bournemouth": "Vitality Stadium",
    "Brentford": "Gtech Community Stadium",
    "Brighton": "Amex Stadium",
    "Chelsea": "Stamford Bridge",
    "Coventry": "Coventry Building Society Arena",
    "Crystal Palace": "Selhurst Park",
    "Everton": "Everton Stadium",
    "Fulham": "Craven Cottage",
    "Hull": "MKM Stadium",
    "Ipswich": "Portman Road",
    "Leeds": "Elland Road",
    "Leicester": "King Power Stadium",
    "Liverpool": "Anfield",
    "Manchester City": "Etihad Stadium",
    "Manchester United": "Old Trafford",
    "Newcastle United": "St. James' Park",
    "Nottingham Forest": "The City Ground",
    "Southampton": "St Mary's Stadium",
    "Sunderland": "Stadium of Light",
    "Tottenham": "Tottenham Hotspur Stadium",
    "West Ham": "London Stadium",
    "Wolverhampton Wanderers": "Molineux Stadium",
}

# Fallback default 2026-27 Gameweek 1 Fixtures
DEFAULT_FIXTURES_2026 = [
    {"fixture_id": 1, "HomeTeam": "Arsenal", "AwayTeam": "Coventry", "Date": "21/08/2026", "Time": "20:00", "Venue": "Emirates Stadium", "Broadcaster": "Sky Sports"},
    {"fixture_id": 2, "HomeTeam": "Hull", "AwayTeam": "Manchester United", "Date": "22/08/2026", "Time": "12:30", "Venue": "MKM Stadium", "Broadcaster": "TNT Sports"},
    {"fixture_id": 3, "HomeTeam": "Everton", "AwayTeam": "Crystal Palace", "Date": "22/08/2026", "Time": "15:00", "Venue": "Everton Stadium", "Broadcaster": None},
    {"fixture_id": 4, "HomeTeam": "Ipswich", "AwayTeam": "Sunderland", "Date": "22/08/2026", "Time": "15:00", "Venue": "Portman Road", "Broadcaster": None},
    {"fixture_id": 5, "HomeTeam": "Nottingham Forest", "AwayTeam": "Leeds", "Date": "22/08/2026", "Time": "15:00", "Venue": "The City Ground", "Broadcaster": None},
    {"fixture_id": 6, "HomeTeam": "Brentford", "AwayTeam": "Tottenham", "Date": "22/08/2026", "Time": "17:30", "Venue": "Gtech Community Stadium", "Broadcaster": "Sky Sports"},
    {"fixture_id": 7, "HomeTeam": "Brighton", "AwayTeam": "Aston Villa", "Date": "23/08/2026", "Time": "14:00", "Venue": "Amex Stadium", "Broadcaster": "Sky Sports"},
    {"fixture_id": 8, "HomeTeam": "Manchester City", "AwayTeam": "Bournemouth", "Date": "23/08/2026", "Time": "14:00", "Venue": "Etihad Stadium", "Broadcaster": "Sky Sports"},
    {"fixture_id": 9, "HomeTeam": "Newcastle United", "AwayTeam": "Liverpool", "Date": "23/08/2026", "Time": "16:30", "Venue": "St. James' Park", "Broadcaster": "Sky Sports"},
    {"fixture_id": 10, "HomeTeam": "Fulham", "AwayTeam": "Chelsea", "Date": "24/08/2026", "Time": "20:00", "Venue": "Craven Cottage", "Broadcaster": "Sky Sports"},
]


def get_current_matchday_fixtures(matchweek: int = 1) -> tuple[str, str, list[dict[str, Any]], list[int], int]:
    """
    Fetch active matchday fixtures from the official 2026/27 fixture list or fallbacks.
    Returns (round_name, season_name, matches, available_matchweeks, current_matchweek).
    """
    available_matchweeks = list(range(1, 39))
    current_mw = matchweek if matchweek and 1 <= matchweek <= 38 else 1
    round_name = f"Gameweek {current_mw}"
    season_name = "2026/27"

    if FIXTURES_FILE_PATH.exists():
        try:
            df = pd.read_csv(FIXTURES_FILE_PATH)
            if "matchweek" in df.columns:
                available_matchweeks = sorted(df["matchweek"].dropna().unique().astype(int).tolist())
                df_mw = df[df["matchweek"] == current_mw]
                
                matches = []
                for _, row in df_mw.iterrows():
                    h_norm = normalize_team_name(str(row.get("home_team", "")))
                    a_norm = normalize_team_name(str(row.get("away_team", "")))
                    venue = TEAM_STADIUMS.get(h_norm, f"{h_norm} Stadium")
                    
                    raw_date = str(row.get("date", "2026-08-21"))
                    if "-" in raw_date:
                        parts = raw_date.split("-")
                        if len(parts) == 3:
                            y, m, d = parts
                            d_str = f"{d}/{m}/{y}"
                        else:
                            d_str = raw_date
                    else:
                        d_str = raw_date
                        
                    raw_time = str(row.get("kickoff_time_uk", "15:00"))
                    t_str = "15:00" if raw_time == "TBC" or pd.isna(row.get("kickoff_time_uk")) else raw_time
                    broadcaster = row.get("tv_broadcaster") if pd.notna(row.get("tv_broadcaster")) and row.get("tv_broadcaster") else None

                    matches.append({
                        "fixture_id": int(row.get("match_number", len(matches) + 1)),
                        "HomeTeam": h_norm,
                        "AwayTeam": a_norm,
                        "Date": d_str,
                        "Time": t_str,
                        "Venue": venue,
                        "Broadcaster": broadcaster,
                    })

                if matches:
                    return round_name, season_name, matches, available_matchweeks, current_mw
        except Exception as e:
            print(f"Error loading fixtures file {FIXTURES_FILE_PATH}: {e}")

    return round_name, season_name, DEFAULT_FIXTURES_2026, available_matchweeks, current_mw


EFL_FILE_PATHS = [
    Path("data/raw/premier/EFL_Championship_25_26_xG.csv"),
    Path("data/raw/premier/championship_2025_26.csv"),
    Path("data/raw/championship_2025_26_xg.csv"),
]
_efl_cache: pd.DataFrame | None = None


def _get_efl_data() -> pd.DataFrame | None:
    """Load and cache 2025/26 EFL Championship match logs with xG."""
    global _efl_cache
    if _efl_cache is not None:
        return _efl_cache
    for p in EFL_FILE_PATHS:
        if p.exists():
            try:
                df = pd.read_csv(p)
                # Standardize column names
                col_map = {}
                for c in df.columns:
                    c_clean = c.strip().lower().replace(" ", "_")
                    if c_clean in ["home_team", "home"]:
                        col_map[c] = "Home"
                    elif c_clean in ["away_team", "away"]:
                        col_map[c] = "Away"
                    elif c_clean in ["home_goals", "fthg", "h_goals"]:
                        col_map[c] = "HomeGoals"
                    elif c_clean in ["away_goals", "ftag", "a_goals"]:
                        col_map[c] = "AwayGoals"
                    elif c_clean in ["home_xg", "hxg", "xg_home"]:
                        col_map[c] = "HomeXG"
                    elif c_clean in ["away_xg", "axg", "xg_away"]:
                        col_map[c] = "AwayXG"
                    elif c_clean in ["score"]:
                        col_map[c] = "Score"
                
                df = df.rename(columns=col_map)
                if "Home" in df.columns and "Away" in df.columns:
                    df = df.dropna(subset=["Home", "Away"])
                    df["HomeNorm"] = df["Home"].apply(normalize_team_name)
                    df["AwayNorm"] = df["Away"].apply(normalize_team_name)
                    _efl_cache = df
                    return _efl_cache
            except Exception as e:
                print(f"Error loading EFL file {p}: {e}")
    return None


def compute_quick_facts(home_team: str, away_team: str, df_history: pd.DataFrame) -> dict[str, Any]:
    """Compute recent form, H2H, season splits, and Elo metrics."""
    h_norm = normalize_team_name(home_team)
    a_norm = normalize_team_name(away_team)
    df_efl = _get_efl_data()
    
    # 1. Recent Form (last 5 matches for each team)
    def _get_form(team_name: str) -> list[dict[str, Any]]:
        t_matches = df_history[(df_history["HomeTeam"] == team_name) | (df_history["AwayTeam"] == team_name)]
        
        # Check if team is a newly promoted side (Coventry, Hull, Ipswich, etc.) or has no recent PL matches
        use_efl = False
        if t_matches.empty:
            use_efl = True
        elif team_name in ["Coventry", "Hull", "Ipswich"]:
            use_efl = True
            
        if use_efl and df_efl is not None:
            efl_matches = df_efl[(df_efl["HomeNorm"] == team_name) | (df_efl["AwayNorm"] == team_name)]
            if not efl_matches.empty:
                last_5 = efl_matches.tail(5)
                form_list = []
                for _, row in last_5.iterrows():
                    is_home = (row["HomeNorm"] == team_name)
                    
                    # Parse goals
                    if "HomeGoals" in row and pd.notna(row["HomeGoals"]) and "AwayGoals" in row and pd.notna(row["AwayGoals"]):
                        try:
                            h_g = int(row["HomeGoals"])
                            a_g = int(row["AwayGoals"])
                        except (ValueError, TypeError):
                            h_g, a_g = 0, 0
                    elif "Score" in row and pd.notna(row["Score"]):
                        score_str = str(row["Score"]).replace("–", "-").strip()
                        parts = score_str.split("-")
                        if len(parts) == 2:
                            try:
                                h_g, a_g = int(parts[0]), int(parts[1])
                            except ValueError:
                                h_g, a_g = 0, 0
                        else:
                            h_g, a_g = 0, 0
                    else:
                        h_g, a_g = 0, 0
                        
                    gf = h_g if is_home else a_g
                    ga = a_g if is_home else h_g
                    opp = row["AwayNorm"] if is_home else row["HomeNorm"]
                    
                    if gf > ga:
                        res = "W"
                    elif gf == ga:
                        res = "D"
                    else:
                        res = "L"
                        
                    # Parse or calibrate xG
                    xg_f = None
                    xg_a = None
                    if "HomeXG" in row and pd.notna(row["HomeXG"]) and "AwayXG" in row and pd.notna(row["AwayXG"]):
                        try:
                            xg_f = float(row["HomeXG"]) if is_home else float(row["AwayXG"])
                            xg_a = float(row["AwayXG"]) if is_home else float(row["HomeXG"])
                        except (ValueError, TypeError):
                            pass
                            
                    if xg_f is None or pd.isna(xg_f):
                        xg_f = round(max(0.4, gf * 0.85 + 0.3), 2)
                    if xg_a is None or pd.isna(xg_a):
                        xg_a = round(max(0.3, ga * 0.85 + 0.3), 2)
                        
                    form_list.append({
                        "result": res,
                        "opponent": opp,
                        "score": f"{gf}-{ga}",
                        "is_home": is_home,
                        "date": str(row.get("Date", "")),
                        "xg_for": round(xg_f, 2),
                        "xg_against": round(xg_a, 2),
                        "league": "EFL Championship",
                    })
                return form_list

        if t_matches.empty:
            return []
        
        last_5 = t_matches.tail(5)
        form_list = []
        for _, row in last_5.iterrows():
            is_home = (row["HomeTeam"] == team_name)
            
            # Extract goals safely
            h_val = row.get("goals_home", row.get("FTHG", row.get("HomeGoals", 0)))
            a_val = row.get("goals_away", row.get("FTAG", row.get("AwayGoals", 0)))
            try:
                h_goals = int(h_val) if pd.notna(h_val) else 0
                a_goals = int(a_val) if pd.notna(a_val) else 0
            except (ValueError, TypeError):
                h_goals, a_goals = 0, 0
                
            gf = h_goals if is_home else a_goals
            ga = a_goals if is_home else h_goals
            opp = row["AwayTeam"] if is_home else row["HomeTeam"]
            
            if gf > ga:
                res = "W"
            elif gf == ga:
                res = "D"
            else:
                res = "L"
                
            xg_f = float(row.get("HXG", 1.5)) if is_home else float(row.get("AXG", 1.2))
            xg_a = float(row.get("AXG", 1.2)) if is_home else float(row.get("HXG", 1.5))
            
            form_list.append({
                "result": res,
                "opponent": opp,
                "score": f"{gf}-{ga}",
                "is_home": is_home,
                "date": str(row.get("Date", "")),
                "xg_for": round(xg_f, 2),
                "xg_against": round(xg_a, 2),
                "league": "Premier League",
            })
        return form_list

    home_form = _get_form(h_norm)
    away_form = _get_form(a_norm)
    
    # Form summary string e.g. "W-W-D-L-W"
    home_form_summary = "-".join([m["result"] for m in home_form]) if home_form else "N/A"
    away_form_summary = "-".join([m["result"] for m in away_form]) if away_form else "N/A"

    # 2. Head-to-Head
    h2h_matches = df_history[
        ((df_history["HomeTeam"] == h_norm) & (df_history["AwayTeam"] == a_norm)) |
        ((df_history["HomeTeam"] == a_norm) & (df_history["AwayTeam"] == h_norm))
    ]
    
    h_wins = 0
    draws = 0
    a_wins = 0
    recent_h2h = []
    
    for _, row in h2h_matches.iterrows():
        is_h_home = (row["HomeTeam"] == h_norm)
        h_val = row.get("goals_home", row.get("FTHG", row.get("HomeGoals", 0)))
        a_val = row.get("goals_away", row.get("FTAG", row.get("AwayGoals", 0)))
        try:
            h_g = int(h_val) if pd.notna(h_val) else 0
            a_g = int(a_val) if pd.notna(a_val) else 0
        except (ValueError, TypeError):
            h_g, a_g = 0, 0
            
        h_res_g = h_g if is_h_home else a_g
        a_res_g = a_g if is_h_home else h_g
        
        if h_res_g > a_res_g:
            h_wins += 1
            winner = h_norm
        elif h_res_g == a_res_g:
            draws += 1
            winner = "Draw"
        else:
            a_wins += 1
            winner = a_norm
            
    for _, row in h2h_matches.tail(5).iterrows():
        h_val = row.get("goals_home", row.get("FTHG", row.get("HomeGoals", 0)))
        a_val = row.get("goals_away", row.get("FTAG", row.get("AwayGoals", 0)))
        try:
            hg = int(h_val) if pd.notna(h_val) else 0
            ag = int(a_val) if pd.notna(a_val) else 0
        except (ValueError, TypeError):
            hg, ag = 0, 0
            
        if hg > ag:
            w_team = row["HomeTeam"]
        elif hg == ag:
            w_team = "Draw"
        else:
            w_team = row["AwayTeam"]
            
        recent_h2h.append({
            "date": str(row.get("Date", "")),
            "home_team": row["HomeTeam"],
            "away_team": row["AwayTeam"],
            "score": f"{hg}-{ag}",
            "winner": w_team,
        })

    # 3. Season Splits (Home Team at Home vs Away Team Away)
    h_home_games = df_history[df_history["HomeTeam"] == h_norm].tail(19)
    a_away_games = df_history[df_history["AwayTeam"] == a_norm].tail(19)
    
    def _calc_split(games: pd.DataFrame, team_name: str, is_home: bool) -> dict[str, Any]:
        if games.empty and df_efl is not None:
            # Calibrate from 2025/26 Championship season with 0.68 conversion factor
            norm_col = "HomeNorm" if is_home else "AwayNorm"
            efl_t_games = df_efl[df_efl[norm_col] == team_name].tail(19)
            if not efl_t_games.empty:
                w = 0
                d = 0
                gfs = []
                gas = []
                for _, row in efl_t_games.iterrows():
                    if "HomeGoals" in row and pd.notna(row["HomeGoals"]) and "AwayGoals" in row and pd.notna(row["AwayGoals"]):
                        try:
                            hg = int(row["HomeGoals"])
                            ag = int(row["AwayGoals"])
                        except (ValueError, TypeError):
                            hg, ag = 0, 0
                    else:
                        score_str = str(row.get("Score", "")).replace("–", "-").strip()
                        parts = score_str.split("-")
                        if len(parts) == 2:
                            try:
                                hg, ag = int(parts[0]), int(parts[1])
                            except ValueError:
                                hg, ag = 0, 0
                        else:
                            hg, ag = 0, 0
                            
                    gf = hg if is_home else ag
                    ga = ag if is_home else hg
                    if gf > ga:
                        w += 1
                    elif gf == ga:
                        d += 1
                    gfs.append(gf)
                    gas.append(ga)
                n = len(gfs)
                if n > 0:
                    l = n - w - d
                    # Apply promotion conversion factor (0.68)
                    return {
                        "matches": n,
                        "wins": w,
                        "draws": d,
                        "losses": l,
                        "win_pct": round((w / n) * 100 * 0.68, 1),
                        "avg_gf": round((sum(gfs) / n) * 0.70, 2),
                        "avg_ga": round((sum(gas) / n) * 1.30, 2),
                        "avg_xg": round((sum(gfs) / n) * 0.70, 2),
                    }

        if games.empty:
            return {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "win_pct": 0, "avg_gf": 0.0, "avg_ga": 0.0, "avg_xg": 0.0}
        n = len(games)
        
        gf_col = "goals_home" if "goals_home" in games.columns else ("FTHG" if "FTHG" in games.columns else "HomeGoals")
        ga_col = "goals_away" if "goals_away" in games.columns else ("FTAG" if "FTAG" in games.columns else "AwayGoals")
        if not is_home:
            gf_col, ga_col = ga_col, gf_col
            
        xg_col = "HXG" if is_home else "AXG"
        
        w = int((games[gf_col] > games[ga_col]).sum()) if gf_col in games.columns and ga_col in games.columns else 0
        d = int((games[gf_col] == games[ga_col]).sum()) if gf_col in games.columns and ga_col in games.columns else 0
        l = n - w - d
        avg_gf = float(games[gf_col].mean()) if gf_col in games.columns else 0.0
        avg_ga = float(games[ga_col].mean()) if ga_col in games.columns else 0.0
        avg_xg = float(games[xg_col].mean()) if xg_col in games.columns else 0.0
        
        return {
            "matches": n,
            "wins": w,
            "draws": d,
            "losses": l,
            "win_pct": round((w / n) * 100, 1) if n > 0 else 0,
            "avg_gf": round(avg_gf, 2),
            "avg_ga": round(avg_ga, 2),
            "avg_xg": round(avg_xg, 2),
        }

    home_split = _calc_split(h_home_games, h_norm, is_home=True)
    away_split = _calc_split(a_away_games, a_norm, is_home=False)

    # 4. Approximate Elo
    elo_base = 1500
    h_pts = (home_split["wins"] * 3 + home_split["draws"]) / max(1, home_split["matches"])
    a_pts = (away_split["wins"] * 3 + away_split["draws"]) / max(1, away_split["matches"])
    
    home_elo = int(elo_base + (h_pts - 1.3) * 150 + (home_split["avg_gf"] - home_split["avg_ga"]) * 60)
    away_elo = int(elo_base + (a_pts - 1.1) * 150 + (away_split["avg_gf"] - away_split["avg_ga"]) * 60)

    return {
        "home_form": home_form,
        "away_form": away_form,
        "home_form_summary": home_form_summary,
        "away_form_summary": away_form_summary,
        "h2h": {
            "total_matches": len(h2h_matches),
            "home_wins": h_wins,
            "draws": draws,
            "away_wins": a_wins,
            "recent_matches": recent_h2h,
        },
        "home_split": home_split,
        "away_split": away_split,
        "elo": {
            "home_elo": home_elo,
            "away_elo": away_elo,
            "diff": home_elo - away_elo,
        },
        "rest_days": {
            "home": 7,
            "away": 7,
        }
    }


def compute_model_explainability(
    home_team: str,
    away_team: str,
    pred_result: dict[str, Any],
    quick_facts: dict[str, Any],
) -> dict[str, Any]:
    """Compute Poisson expected goals, top scoreline probabilities, and narrative explanation."""
    h_norm = normalize_team_name(home_team)
    a_norm = normalize_team_name(away_team)
    
    # Estimate lambda based on team splits and probability outputs
    prob_h = pred_result.get("prob_home", 0.45)
    prob_d = pred_result.get("prob_draw", 0.28)
    prob_a = pred_result.get("prob_away", 0.27)
    
    # Base expected goals
    lambda_h = max(0.4, 1.45 + (prob_h - prob_a) * 1.5 + 0.20)
    lambda_a = max(0.3, 1.15 - (prob_h - prob_a) * 0.8)
    
    # Exact score probability distribution (Bivariate Poisson)
    scores = []
    for h in range(6):
        for a in range(6):
            p = float(poisson.pmf(h, lambda_h) * poisson.pmf(a, lambda_a))
            scores.append({"score": f"{h}-{a}", "home_goals": h, "away_goals": a, "prob": p})
            
    # Normalize score probabilities
    total_p = sum(s["prob"] for s in scores)
    for s in scores:
        s["prob"] = round(s["prob"] / total_p, 4)
        s["pct"] = round(s["prob"] * 100, 1)
        
    scores.sort(key=lambda x: x["prob"], reverse=True)
    top_5_scores = scores[:5]
    
    pred_label = pred_result.get("prediction", "H")
    
    # Ensure the most likely score matches the predicted outcome
    matching_scores = [s for s in scores if (pred_label == "H" and s["home_goals"] > s["away_goals"]) or 
                                            (pred_label == "A" and s["away_goals"] > s["home_goals"]) or 
                                            (pred_label == "D" and s["home_goals"] == s["away_goals"])]
    most_likely_score = matching_scores[0]["score"] if matching_scores else (top_5_scores[0]["score"] if top_5_scores else "1-1")

    # Tactical comparison metrics (0-100 scale)
    h_att = min(98, max(40, int(50 + (lambda_h - 1.3) * 35)))
    h_def = min(98, max(40, int(50 + (1.5 - lambda_a) * 30)))
    a_att = min(98, max(40, int(50 + (lambda_a - 1.1) * 35)))
    a_def = min(98, max(40, int(50 + (1.7 - lambda_h) * 30)))

    # Dynamic Narrative Builder
    
    if pred_label == "H":
        edge_text = f"{h_norm}'s projected attacking output ({lambda_h:.2f} xG) outperforms {a_norm}'s road defense ({lambda_a:.2f} expected goals conceded)."
        narrative = (
            f"The model projects {h_norm} as favorites with a {prob_h*100:.1f}% win probability. "
            f"{edge_text} Coupled with a historical home advantage factor (+0.22 λ boost) and positive recent momentum ({quick_facts['home_form_summary']}), "
            f"the most probable scoreline is {most_likely_score} ({top_5_scores[0]['pct']}%)."
        )
    elif pred_label == "A":
        edge_text = f"{a_norm}'s tactical efficiency and offensive quality ({lambda_a:.2f} projected xG) give them a distinct edge over {h_norm}'s backline."
        
        away_elo = quick_facts['elo']['away_elo']
        home_elo = quick_facts['elo']['home_elo']
        elo_text = (
            f"{a_norm}'s superior Elo rating ({away_elo} vs {home_elo})"
            if away_elo > home_elo
            else f"{a_norm}'s tactical metrics overcome their Elo deficit ({away_elo} vs {home_elo})"
        )
        
        narrative = (
            f"The model favors an away victory for {a_norm} with a {prob_a*100:.1f}% probability. "
            f"{edge_text} Despite {h_norm}'s home crowd, {elo_text} "
            f"drives the outcome, with {most_likely_score} predicted as the top exact scoreline."
        )
    else:
        narrative = (
            f"The model predicts a tightly contested stalemate between {h_norm} and {a_norm} with a {prob_d*100:.1f}% draw probability. "
            f"Both squads demonstrate evenly matched expected metrics (projected {lambda_h:.2f} xG vs {lambda_a:.2f} xG). "
            f"The most likely scorelines are {top_5_scores[0]['score']} and {top_5_scores[1]['score']}."
        )

    return {
        "lambda_home": round(lambda_h, 2),
        "lambda_away": round(lambda_a, 2),
        "most_likely_score": most_likely_score,
        "top_scores": top_5_scores,
        "tactical_ratings": {
            "home_attack": h_att,
            "home_defense": h_def,
            "away_attack": a_att,
            "away_defense": a_def,
        },
        "key_factors": [
            {"factor": "Projected Expected Goals", "home_val": f"{lambda_h:.2f} xG", "away_val": f"{lambda_a:.2f} xG"},
            {"factor": "Current Elo Rating", "home_val": f"{quick_facts['elo']['home_elo']}", "away_val": f"{quick_facts['elo']['away_elo']}"},
            {"factor": "Recent Form (Last 5)", "home_val": quick_facts["home_form_summary"], "away_val": quick_facts["away_form_summary"]},
            {"factor": "Venue Split Win %", "home_val": f"{quick_facts['home_split']['win_pct']}% (Home)", "away_val": f"{quick_facts['away_split']['win_pct']}% (Away)"},
        ],
        "narrative": narrative,
    }


def get_matchday_overview(
    matchweek: int = 1, 
    force_recompute: bool = False,
    config: dict = None,
    model=None,
    df_history: pd.DataFrame = None
) -> dict[str, Any]:
    """Assemble complete matchday data with predictions, quick facts, and explainability."""
    cache_dir = Path("data/cache")
    cache_file = cache_dir / f"matchweek_{matchweek}.json"
    
    if not force_recompute and cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache for matchweek {matchweek}: {e}")

    round_name, season_name, fixtures, available_matchweeks, current_mw = get_current_matchday_fixtures(matchweek)
    
    if config is None:
        config = load_config(CONFIG_PATH)
        
    if df_history is None:
        df_history = load_matches(
            csv_path=config["data"].get("csv_path"),
            csv_glob=config["data"].get("csv_glob")
        )
    
    # 1. Run inference on all matchday fixtures
    pred_results = predict_fixtures(config, fixtures, model=model, df_history=df_history)
    
    matches_payload = []
    home_wins = 0
    draws = 0
    away_wins = 0
    
    for i, fix in enumerate(fixtures):
        p_res = pred_results[i] if i < len(pred_results) else {
            "prediction": "H", "prob_home": 0.5, "prob_draw": 0.3, "prob_away": 0.2
        }
        
        pred = p_res.get("prediction", "H")
        if pred == "H":
            home_wins += 1
        elif pred == "D":
            draws += 1
        else:
            away_wins += 1
            
        prob_h = p_res.get("prob_home", 0.45)
        prob_d = p_res.get("prob_draw", 0.28)
        prob_a = p_res.get("prob_away", 0.27)
        max_prob = max(prob_h, prob_a)
        
        if max_prob >= 0.58:
            conf_label = "High Confidence"
            conf_class = "confidence-high"
        elif max_prob >= 0.48:
            conf_label = "Moderate Confidence"
            conf_class = "confidence-med"
        else:
            conf_label = "Toss Up"
            conf_class = "confidence-low"

        # Compute Quick Facts & Explainability
        odds = get_match_odds(fix["HomeTeam"], fix["AwayTeam"])
        quick_facts = compute_quick_facts(fix["HomeTeam"], fix["AwayTeam"], df_history)
        explanation = compute_model_explainability(fix["HomeTeam"], fix["AwayTeam"], p_res, quick_facts)
        
        matches_payload.append({
            "fixture_id": fix.get("fixture_id", i + 1),
            "home_team": normalize_team_name(fix["HomeTeam"]),
            "away_team": normalize_team_name(fix["AwayTeam"]),
            "date": fix.get("Date", "21/08/2026"),
            "time": fix.get("Time", "15:00"),
            "venue": fix.get("Venue", "Premier League"),
            "broadcaster": fix.get("Broadcaster"),
            "prediction": pred,
            "prob_home": round(prob_h, 3),
            "prob_draw": round(prob_d, 3),
            "prob_away": round(prob_a, 3),
            "confidence_label": conf_label,
            "confidence_class": conf_class,
            "most_likely_score": explanation["most_likely_score"],
            "quick_facts": quick_facts,
            "explanation": explanation,
            "odds": odds,
        })
        
    result = {
        "round": round_name,
        "season": season_name,
        "current_matchweek": current_mw,
        "available_matchweeks": available_matchweeks,
        "total_fixtures": len(matches_payload),
        "summary": {
            "predicted_home_wins": home_wins,
            "predicted_draws": draws,
            "predicted_away_wins": away_wins,
        },
        "matches": matches_payload,
    }
    
    # Save to cache
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(result, f)
    except Exception as e:
        print(f"Error saving cache for matchweek {matchweek}: {e}")
        
    return result

def precompute_season_cache(start_mw: int = 1, end_mw: int = 38) -> None:
    """Precompute and save cache for a range of matchweeks."""
    print(f"Precomputing matchday cache for matchweeks {start_mw} to {end_mw}...")
    for mw in range(start_mw, end_mw + 1):
        print(f"Computing MW {mw}...")
        get_matchday_overview(mw, force_recompute=True)
    print("Cache generation complete!")
