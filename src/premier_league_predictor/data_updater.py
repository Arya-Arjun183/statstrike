import os
import pandas as pd
import requests
from io import StringIO
from pathlib import Path
from premier_league_predictor.data import normalize_team_name
from premier_league_predictor.config import load_config
from premier_league_predictor.training import train_from_config

MAIN_DATASET_PATH = Path("data/raw/premier/epl-xg-data2014-26.csv")

def calculate_proxy_xg(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate xG proxy using shots, shots on target, corners, and goals if HXG/AXG missing."""
    df = df.copy()
    
    if "HXG" not in df.columns or df["HXG"].isnull().all():
        hst = df["HST"].fillna(df["FTHG"] if "FTHG" in df.columns else 1) if "HST" in df.columns else df.get("FTHG", 1)
        hs = df["HS"].fillna(hst * 2.5) if "HS" in df.columns else hst * 2.5
        hc = df["HC"].fillna(4.0) if "HC" in df.columns else 4.0
        fthg = df["FTHG"].fillna(0) if "FTHG" in df.columns else 0
        df["HXG"] = (hst * 0.28 + (hs - hst) * 0.04 + hc * 0.03 + fthg * 0.20).round(2)
        
    if "AXG" not in df.columns or df["AXG"].isnull().all():
        ast = df["AST"].fillna(df["FTAG"] if "FTAG" in df.columns else 1) if "AST" in df.columns else df.get("FTAG", 1)
        as_shots = df["AS"].fillna(ast * 2.5) if "AS" in df.columns else ast * 2.5
        ac = df["AC"].fillna(3.5) if "AC" in df.columns else 3.5
        ftag = df["FTAG"].fillna(0) if "FTAG" in df.columns else 0
        df["AXG"] = (ast * 0.28 + (as_shots - ast) * 0.04 + ac * 0.03 + ftag * 0.20).round(2)
        
    return df

def download_football_data_season(season_code: str = "2526") -> pd.DataFrame:
    """
    Download free, publicly maintained match results directly from Football-Data.co.uk.
    Example season_code: '2526' (2025/26), '2627' (2026/27).
    No API key or rate limit required.
    """
    url = f"https://www.football-data.co.uk/mmz4252/{season_code}/E0.csv"
    print(f"Fetching free match results from Football-Data.co.uk ({url})...")
    
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        raise RuntimeError(f"Could not download {url} (HTTP {resp.status_code})")
        
    df = pd.read_csv(StringIO(resp.text))
    # Keep completed matches
    df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    df["HomeTeam"] = df["HomeTeam"].apply(normalize_team_name)
    df["AwayTeam"] = df["AwayTeam"].apply(normalize_team_name)
    
    # Format season
    start_yr = int("20" + season_code[:2])
    end_yr = int("20" + season_code[2:])
    df["Season"] = f"{start_yr}-{end_yr}"
    
    df = calculate_proxy_xg(df)
    print(f"Downloaded {len(df)} completed matches for season {df['Season'].iloc[0]}.")
    return df

def ingest_weekly_csv(file_path: str, season: str = "2026-2027") -> int:
    """
    Ingest a weekly match CSV provided by user, format it, and merge into master dataset.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    df_new = pd.read_csv(path)
    if "HomeTeam" not in df_new.columns or "AwayTeam" not in df_new.columns:
        raise ValueError("CSV must contain 'HomeTeam' and 'AwayTeam' columns.")
        
    df_new["HomeTeam"] = df_new["HomeTeam"].apply(normalize_team_name)
    df_new["AwayTeam"] = df_new["AwayTeam"].apply(normalize_team_name)
    
    if "Season" not in df_new.columns:
        df_new["Season"] = season
        
    df_new = calculate_proxy_xg(df_new)
    
    # Load main dataset
    if MAIN_DATASET_PATH.exists():
        df_master = pd.read_csv(MAIN_DATASET_PATH)
    else:
        df_master = pd.DataFrame()
        
    # Deduplicate against master (by Date + HomeTeam + AwayTeam)
    if not df_master.empty and "Date" in df_master.columns and "Date" in df_new.columns:
        keys_existing = set(zip(df_master["Date"].astype(str), df_master["HomeTeam"], df_master["AwayTeam"]))
        new_records = []
        for _, row in df_new.iterrows():
            k = (str(row["Date"]), row["HomeTeam"], row["AwayTeam"])
            if k not in keys_existing:
                new_records.append(row)
        if not new_records:
            print("All matches in CSV already exist in the master dataset.")
            return 0
        df_to_add = pd.DataFrame(new_records)
    else:
        df_to_add = df_new

    df_combined = pd.concat([df_master, df_to_add], ignore_index=True)
    df_combined.to_csv(MAIN_DATASET_PATH, index=False)
    print(f"Successfully added {len(df_to_add)} matches to {MAIN_DATASET_PATH}.")
    return len(df_to_add)

def fetch_understat_season(season: str = "2025") -> int:
    """
    Fetch exact match outcomes and xG directly from Understat without any API keys.
    season can be '2024', '2025', '2026', etc.
    """
    from understatapi import UnderstatClient
    print(f"Fetching open Understat match & xG data for Premier League season {season}...")
    
    understat = UnderstatClient()
    try:
        matches = understat.league(league="EPL").get_match_data(season=season)
    except Exception as e:
        print(f"Understat fetch failed: {e}")
        return 0
        
    start_yr = int(season)
    season_str = f"{start_yr}-{start_yr + 1}"
    
    new_rows = []
    for m in matches:
        if not m.get("isResult"):
            continue
            
        dt = m.get("datetime", "")
        if " " in dt:
            d_part = dt.split(" ")[0]
            y, mo, d = d_part.split("-")
            date_formatted = f"{d}/{mo}/{y}"
        else:
            date_formatted = dt
            
        home_team = normalize_team_name(m["h"]["title"])
        away_team = normalize_team_name(m["a"]["title"])
        goals_home = int(m["goals"]["h"]) if m.get("goals") and m["goals"].get("h") is not None else 0
        goals_away = int(m["goals"]["a"]) if m.get("goals") and m["goals"].get("a") is not None else 0
        hxg = round(float(m["xG"]["h"]), 2) if m.get("xG") and m["xG"].get("h") is not None else 0.0
        axg = round(float(m["xG"]["a"]), 2) if m.get("xG") and m["xG"].get("a") is not None else 0.0
        
        new_rows.append({
            "Date": date_formatted,
            "HomeTeam": home_team,
            "AwayTeam": away_team,
            "FTHG": goals_home,
            "FTAG": goals_away,
            "goals_home": goals_home,
            "goals_away": goals_away,
            "HXG": hxg,
            "AXG": axg,
            "Season": season_str,
        })
        
    if not new_rows:
        print(f"No completed matches found on Understat for season {season}.")
        return 0
        
    df_new = pd.DataFrame(new_rows)
    
    # Load main dataset
    if MAIN_DATASET_PATH.exists():
        df_master = pd.read_csv(MAIN_DATASET_PATH)
    else:
        df_master = pd.DataFrame()
        
    # Deduplicate against master (by Date + HomeTeam + AwayTeam)
    if not df_master.empty and "Date" in df_master.columns:
        keys_existing = set(zip(df_master["Date"].astype(str), df_master["HomeTeam"], df_master["AwayTeam"]))
        to_add = [row for _, row in df_new.iterrows() if (str(row["Date"]), row["HomeTeam"], row["AwayTeam"]) not in keys_existing]
        if not to_add:
            print("All Understat matches are already in the master dataset.")
            return 0
        df_to_add = pd.DataFrame(to_add)
    else:
        df_to_add = df_new

    df_combined = pd.concat([df_master, df_to_add], ignore_index=True)
    df_combined.to_csv(MAIN_DATASET_PATH, index=False)
    print(f"Successfully added {len(df_to_add)} matches with exact Understat xG to {MAIN_DATASET_PATH}.")
    return len(df_to_add)

def update_and_retrain(config_path: str = "configs/test_xg_efficient.yaml"):
    """Retrain model on updated dataset."""
    print(f"Retraining model using {config_path}...")
    cfg = load_config(config_path)
    metrics = train_from_config(cfg)
    print(f"Model retrained successfully! Holdout accuracy={metrics.get('accuracy', 0.0):.4f}")
    
    # Automatically rebuild cache after training
    from premier_league_predictor.matchday import precompute_season_cache
    precompute_season_cache()
    
    return metrics
