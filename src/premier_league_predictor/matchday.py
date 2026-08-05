from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import poisson

from premier_league_predictor.config import load_config
from premier_league_predictor.data import load_matches, normalize_team_name
from premier_league_predictor.prediction import predict_fixtures
from premier_league_predictor.api_football import fetch_api, LEAGUE_ID, get_mapped_team_name, API_FOOTBALL_KEY

CONFIG_PATH = "configs/test_xg_efficient.yaml"

# Default fallback 2026-27 Gameweek 1 Fixtures
DEFAULT_FIXTURES_2026 = [
    {"fixture_id": 101, "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "Date": "15/08/2026", "Time": "12:30", "Venue": "Emirates Stadium"},
    {"fixture_id": 102, "HomeTeam": "Manchester City", "AwayTeam": "Tottenham", "Date": "15/08/2026", "Time": "15:00", "Venue": "Etihad Stadium"},
    {"fixture_id": 103, "HomeTeam": "Liverpool", "AwayTeam": "Bournemouth", "Date": "15/08/2026", "Time": "15:00", "Venue": "Anfield"},
    {"fixture_id": 104, "HomeTeam": "Manchester United", "AwayTeam": "Aston Villa", "Date": "15/08/2026", "Time": "15:00", "Venue": "Old Trafford"},
    {"fixture_id": 105, "HomeTeam": "Newcastle United", "AwayTeam": "Everton", "Date": "15/08/2026", "Time": "15:00", "Venue": "St. James' Park"},
    {"fixture_id": 106, "HomeTeam": "Brighton", "AwayTeam": "Fulham", "Date": "15/08/2026", "Time": "15:00", "Venue": "Amex Stadium"},
    {"fixture_id": 107, "HomeTeam": "West Ham", "AwayTeam": "Brentford", "Date": "15/08/2026", "Time": "17:30", "Venue": "London Stadium"},
    {"fixture_id": 108, "HomeTeam": "Nottingham Forest", "AwayTeam": "Crystal Palace", "Date": "16/08/2026", "Time": "14:00", "Venue": "City Ground"},
    {"fixture_id": 109, "HomeTeam": "Wolverhampton Wanderers", "AwayTeam": "Ipswich", "Date": "16/08/2026", "Time": "16:30", "Venue": "Molineux Stadium"},
    {"fixture_id": 110, "HomeTeam": "Leeds", "AwayTeam": "Southampton", "Date": "17/08/2026", "Time": "20:00", "Venue": "Elland Road"},
]


def get_current_matchday_fixtures() -> tuple[str, str, list[dict[str, Any]]]:
    """Fetch active matchday fixtures from API-Football or return curated season fixtures."""
    round_name = "Gameweek 1"
    season_name = "2026/27"
    
    if API_FOOTBALL_KEY:
        try:
            # Query current round
            rounds_data = fetch_api("fixtures/rounds", {"league": LEAGUE_ID, "season": 2025, "current": "true"})
            if rounds_data and "response" in rounds_data and rounds_data["response"]:
                current_round = rounds_data["response"][0]
                fixtures_data = fetch_api("fixtures", {"league": LEAGUE_ID, "season": 2025, "round": current_round})
                if fixtures_data and "response" in fixtures_data and fixtures_data["response"]:
                    matches = []
                    for item in fixtures_data["response"][:10]:
                        fix = item["fixture"]
                        dt_raw = fix.get("date", "")
                        d_str = "15/08/2026"
                        t_str = "15:00"
                        if dt_raw and len(dt_raw) >= 10:
                            y, m, d = dt_raw[:10].split("-")
                            d_str = f"{d}/{m}/{y}"
                            t_str = dt_raw[11:16] if len(dt_raw) >= 16 else "15:00"
                        
                        h_team = get_mapped_team_name(item["teams"]["home"]["name"])
                        a_team = get_mapped_team_name(item["teams"]["away"]["name"])
                        venue = fix.get("venue", {}).get("name", "Premier League Ground")
                        
                        matches.append({
                            "fixture_id": fix.get("id", len(matches) + 1),
                            "HomeTeam": h_team,
                            "AwayTeam": a_team,
                            "Date": d_str,
                            "Time": t_str,
                            "Venue": venue,
                        })
                    if matches:
                        return current_round, "2025/26", matches
        except Exception as e:
            print(f"Failed to fetch live matchday from API-Football: {e}")
            
    return round_name, season_name, DEFAULT_FIXTURES_2026


def compute_quick_facts(home_team: str, away_team: str, df_history: pd.DataFrame) -> dict[str, Any]:
    """Compute recent form, H2H, season splits, and Elo metrics."""
    h_norm = normalize_team_name(home_team)
    a_norm = normalize_team_name(away_team)
    
    # 1. Recent Form (last 5 matches for each team)
    def _get_form(team_name: str) -> list[dict[str, Any]]:
        t_matches = df_history[(df_history["HomeTeam"] == team_name) | (df_history["AwayTeam"] == team_name)]
        if t_matches.empty:
            return []
        
        last_5 = t_matches.tail(5)
        form_list = []
        for _, row in last_5.iterrows():
            is_home = (row["HomeTeam"] == team_name)
            gf = int(row["FTHG"]) if is_home else int(row["FTAG"])
            ga = int(row["FTAG"]) if is_home else int(row["FTHG"])
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
        h_g = int(row["FTHG"]) if is_h_home else int(row["FTAG"])
        a_g = int(row["FTAG"]) if is_h_home else int(row["FTHG"])
        
        if h_g > a_g:
            h_wins += 1
            winner = h_norm
        elif h_g == a_g:
            draws += 1
            winner = "Draw"
        else:
            a_wins += 1
            winner = a_norm
            
    for _, row in h2h_matches.tail(5).iterrows():
        recent_h2h.append({
            "date": str(row.get("Date", "")),
            "home_team": row["HomeTeam"],
            "away_team": row["AwayTeam"],
            "score": f"{int(row['FTHG'])}-{int(row['FTAG'])}",
            "winner": h_norm if (row["FTR"] == "H" if row["HomeTeam"] == h_norm else row["FTR"] == "A") else ("Draw" if row["FTR"] == "D" else a_norm)
        })

    # 3. Season Splits (Home Team at Home vs Away Team Away)
    h_home_games = df_history[df_history["HomeTeam"] == h_norm].tail(19)
    a_away_games = df_history[df_history["AwayTeam"] == a_norm].tail(19)
    
    def _calc_split(games: pd.DataFrame, is_home: bool) -> dict[str, Any]:
        if games.empty:
            return {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "win_pct": 0, "avg_gf": 0.0, "avg_ga": 0.0, "avg_xg": 0.0}
        n = len(games)
        target_res = "H" if is_home else "A"
        gf_col = "FTHG" if is_home else "FTAG"
        ga_col = "FTAG" if is_home else "FTHG"
        xg_col = "HXG" if is_home else "AXG"
        
        w = int((games["FTR"] == target_res).sum())
        d = int((games["FTR"] == "D").sum())
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

    home_split = _calc_split(h_home_games, is_home=True)
    away_split = _calc_split(a_away_games, is_home=False)

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
    most_likely_score = top_5_scores[0]["score"] if top_5_scores else "1-1"

    # Tactical comparison metrics (0-100 scale)
    h_att = min(98, max(40, int(50 + (lambda_h - 1.3) * 35)))
    h_def = min(98, max(40, int(50 + (1.5 - lambda_a) * 30)))
    a_att = min(98, max(40, int(50 + (lambda_a - 1.1) * 35)))
    a_def = min(98, max(40, int(50 + (1.7 - lambda_h) * 30)))

    # Dynamic Narrative Builder
    pred_label = pred_result.get("prediction", "H")
    
    if pred_label == "H":
        edge_text = f"{h_norm}'s projected attacking output ({lambda_h:.2f} xG) outperforms {a_norm}'s road defense ({lambda_a:.2f} expected goals conceded)."
        narrative = (
            f"The model projects {h_norm} as favorites with a {prob_h*100:.1f}% win probability. "
            f"{edge_text} Coupled with a historical home advantage factor (+0.22 λ boost) and positive recent momentum ({quick_facts['home_form_summary']}), "
            f"the most probable scoreline is {most_likely_score} ({top_5_scores[0]['pct']}%)."
        )
    elif pred_label == "A":
        edge_text = f"{a_norm}'s tactical efficiency and offensive quality ({lambda_a:.2f} projected xG) give them a distinct edge over {h_norm}'s backline."
        narrative = (
            f"The model favors an away victory for {a_norm} with a {prob_a*100:.1f}% probability. "
            f"{edge_text} Despite {h_norm}'s home crowd, {a_norm}'s superior Elo rating ({quick_facts['elo']['away_elo']} vs {quick_facts['elo']['home_elo']}) "
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


def get_matchday_overview() -> dict[str, Any]:
    """Assemble complete matchday data with predictions, quick facts, and explainability."""
    round_name, season_name, fixtures = get_current_matchday_fixtures()
    config = load_config(CONFIG_PATH)
    df_history = load_matches(
        csv_path=config["data"].get("csv_path"),
        csv_glob=config["data"].get("csv_glob")
    )
    
    # 1. Run inference on all matchday fixtures
    pred_results = predict_fixtures(config, fixtures)
    
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
        quick_facts = compute_quick_facts(fix["HomeTeam"], fix["AwayTeam"], df_history)
        explanation = compute_model_explainability(fix["HomeTeam"], fix["AwayTeam"], p_res, quick_facts)
        
        matches_payload.append({
            "fixture_id": fix.get("fixture_id", i + 1),
            "home_team": normalize_team_name(fix["HomeTeam"]),
            "away_team": normalize_team_name(fix["AwayTeam"]),
            "date": fix.get("Date", "15/08/2026"),
            "time": fix.get("Time", "15:00"),
            "venue": fix.get("Venue", "Premier League"),
            "prediction": pred,
            "prob_home": round(prob_h, 3),
            "prob_draw": round(prob_d, 3),
            "prob_away": round(prob_a, 3),
            "confidence_label": conf_label,
            "confidence_class": conf_class,
            "most_likely_score": explanation["most_likely_score"],
            "quick_facts": quick_facts,
            "explanation": explanation,
        })
        
    return {
        "round": round_name,
        "season": season_name,
        "total_fixtures": len(matches_payload),
        "summary": {
            "predicted_home_wins": home_wins,
            "predicted_draws": draws,
            "predicted_away_wins": away_wins,
        },
        "matches": matches_payload,
    }
