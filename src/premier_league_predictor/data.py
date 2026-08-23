from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


CANONICAL_TEAM_NAMES: dict[str, str] = {
    # Manchester United
    "man utd": "Manchester United",
    "man united": "Manchester United",
    "manchester united": "Manchester United",
    "manchester utd": "Manchester United",
    "man_united": "Manchester United",
    
    # Manchester City
    "man city": "Manchester City",
    "manchester city": "Manchester City",
    "man_city": "Manchester City",
    
    # Newcastle
    "newcastle": "Newcastle United",
    "newcastle united": "Newcastle United",
    "newcastle utd": "Newcastle United",
    
    # Nottingham Forest
    "nott'm forest": "Nottingham Forest",
    "notts forest": "Nottingham Forest",
    "nottingham forest": "Nottingham Forest",
    "nottingham": "Nottingham Forest",
    
    # Wolves
    "wolves": "Wolverhampton Wanderers",
    "wolverhampton": "Wolverhampton Wanderers",
    "wolverhampton wanderers": "Wolverhampton Wanderers",
    
    # Tottenham
    "tottenham": "Tottenham",
    "tottenham hotspur": "Tottenham",
    "spurs": "Tottenham",
    
    # West Ham
    "west ham": "West Ham",
    "west ham united": "West Ham",
    "west ham utd": "West Ham",
    
    # Brighton
    "brighton": "Brighton",
    "brighton & hove albion": "Brighton",
    "brighton and hove albion": "Brighton",
    
    # Sheffield United
    "sheffield utd": "Sheffield United",
    "sheffield united": "Sheffield United",
    "sheffield u": "Sheffield United",
    
    # Leeds
    "leeds": "Leeds",
    "leeds united": "Leeds",
    
    # Leicester
    "leicester": "Leicester",
    "leicester city": "Leicester",
    
    # West Brom
    "west brom": "West Bromwich Albion",
    "west bromwich albion": "West Bromwich Albion",
    "west bromwich": "West Bromwich Albion",
    
    # QPR
    "qpr": "Queens Park Rangers",
    "queens park rangers": "Queens Park Rangers",
    
    # Luton
    "luton": "Luton",
    "luton town": "Luton",
    
    # Ipswich
    "ipswich": "Ipswich",
    "ipswich town": "Ipswich",
    
    # Norwich
    "norwich": "Norwich",
    "norwich city": "Norwich",
    
    # Huddersfield
    "huddersfield": "Huddersfield",
    "huddersfield town": "Huddersfield",
    
    # Cardiff
    "cardiff": "Cardiff",
    "cardiff city": "Cardiff",
    
    # Swansea
    "swansea": "Swansea",
    "swansea city": "Swansea",
    
    # Bournemouth
    "afc bournemouth": "Bournemouth",
    "bournemouth": "Bournemouth",

    # Coventry
    "coventry": "Coventry",
    "coventry city": "Coventry",

    # Sunderland
    "sunderland": "Sunderland",
    "sunderland afc": "Sunderland",

    # Hull
    "hull": "Hull",
    "hull city": "Hull",
    
    # Stoke
    "stoke": "Stoke",
    "stoke city": "Stoke",
}


def normalize_team_name(name: str | None) -> str:
    """Normalize various team name formats to canonical representation."""
    if not name or not isinstance(name, str):
        return str(name)
    cleaned = name.strip().lower()
    return CANONICAL_TEAM_NAMES.get(cleaned, name.strip())


def _resolve_paths(csv_path: str | Path | None, csv_glob: str | None) -> list[Path]:
    if csv_glob:
        paths = sorted(Path().glob(csv_glob))
        if paths:
            return paths

    if csv_path is None:
        raise ValueError("Either data.csv_path or data.csv_glob must be provided")

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return [path]


def _read_csv_with_season(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).copy()  # defragment wide CSVs
    
    # Normalize team names
    if "HomeTeam" in df.columns:
        df["HomeTeam"] = df["HomeTeam"].apply(normalize_team_name)
    if "AwayTeam" in df.columns:
        df["AwayTeam"] = df["AwayTeam"].apply(normalize_team_name)

    # Normalize columns for xG datasets
    if "goals_home" in df.columns:
        if "FTHG" not in df.columns:
            df["FTHG"] = df["goals_home"]
        else:
            df["FTHG"] = df["FTHG"].fillna(df["goals_home"])
            
    if "goals_away" in df.columns:
        if "FTAG" not in df.columns:
            df["FTAG"] = df["goals_away"]
        else:
            df["FTAG"] = df["FTAG"].fillna(df["goals_away"])
        
    if "FTHG" in df.columns and "FTAG" in df.columns and "FTR" not in df.columns:
        df["FTR"] = "D"
        df.loc[df["FTHG"] > df["FTAG"], "FTR"] = "H"
        df.loc[df["FTHG"] < df["FTAG"], "FTR"] = "A"

    if "Date" in df.columns:
        # Convert Date to datetime temporarily to extract season
        dt = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        year = dt.dt.year.fillna(0).astype(int)
        month = dt.dt.month.fillna(0).astype(int)
        # season is year if month >= 8, else year-1
        start_year = np.where(month >= 8, year, year - 1)
        df["season"] = [f"{sy}-{sy+1}" if sy > 0 else path.stem for sy in start_year]
    else:
        df["season"] = path.stem
        
    return df


def _concat_dataframes(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    merged = pd.concat(frames, ignore_index=True)
    if "Date" in merged.columns:
        merged["Date"] = pd.to_datetime(merged["Date"], dayfirst=True, errors="coerce")
        merged = merged.sort_values("Date").reset_index(drop=True)
    return merged.copy()  # defragment


def load_matches(csv_path: str | Path | None = None, csv_glob: str | None = None) -> pd.DataFrame:
    paths = _resolve_paths(csv_path=csv_path, csv_glob=csv_glob)
    frames = [_read_csv_with_season(path) for path in paths]
    
    # Append API-Football cache if available
    cache_path = Path("data/raw/premier/api-football-cache.csv")
    if cache_path.exists():
        try:
            api_cache = _read_csv_with_season(cache_path)
            if not api_cache.empty:
                frames.append(api_cache)
        except Exception as e:
            print(f"Warning: Failed to load api-football-cache.csv: {e}")
            
    df = _concat_dataframes(frames)
    
    # Remove duplicate matches (e.g. if a match is both in the raw CSV and the cache)
    if "Date" in df.columns and "HomeTeam" in df.columns and "AwayTeam" in df.columns:
        df = df.drop_duplicates(subset=["Date", "HomeTeam", "AwayTeam"], keep="last").reset_index(drop=True)
        
    return df
