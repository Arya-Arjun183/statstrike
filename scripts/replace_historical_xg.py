import os
import pandas as pd
from pathlib import Path
from understatapi import UnderstatClient
import sys

# Add src to path so we can import from premier_league_predictor
sys.path.append(os.path.abspath("src"))

from premier_league_predictor.data import normalize_team_name

MAIN_DATASET_PATH = Path("data/raw/premier/epl-xg-data2014-26.csv")

def run():
    print(f"Loading master dataset from {MAIN_DATASET_PATH}...")
    df_master = pd.read_csv(MAIN_DATASET_PATH)
    
    understat = UnderstatClient()
    
    updated_count = 0
    
    for year in range(2014, 2026):
        season_str = str(year)
        print(f"Fetching Understat data for {season_str}...")
        try:
            matches = understat.league(league="EPL").get_match_data(season=season_str)
        except Exception as e:
            print(f"Failed to fetch {season_str}: {e}")
            continue
            
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
            hxg = round(float(m["xG"]["h"]), 2) if m.get("xG") and m["xG"].get("h") is not None else 0.0
            axg = round(float(m["xG"]["a"]), 2) if m.get("xG") and m["xG"].get("a") is not None else 0.0
            
            mask = (
                (df_master["Date"] == date_formatted) & 
                (df_master["HomeTeam"] == home_team) & 
                (df_master["AwayTeam"] == away_team)
            )
            
            if not mask.any():
                # Try just Home and Away with goals to see if date was off by 1 day
                try:
                    goals_home = int(m["goals"]["h"])
                    goals_away = int(m["goals"]["a"])
                    mask_fallback = (
                        (df_master["HomeTeam"] == home_team) & 
                        (df_master["AwayTeam"] == away_team) &
                        (df_master["goals_home"] == goals_home) &
                        (df_master["goals_away"] == goals_away)
                    )
                    if mask_fallback.any():
                        # Pick the first match in the same season timeframe
                        idx_candidates = df_master[mask_fallback].index
                        for idx in idx_candidates:
                            match_date = str(df_master.loc[idx, "Date"])
                            if str(year) in match_date or str(year+1) in match_date:
                                mask = (df_master.index == idx)
                                break
                except Exception:
                    pass

            if mask.any():
                idx = mask.idxmax()
                
                # Check if xG is different
                old_hxg = df_master.loc[idx, "HXG"]
                old_axg = df_master.loc[idx, "AXG"]
                
                if pd.isna(old_hxg) or pd.isna(old_axg) or abs(old_hxg - hxg) > 0.01 or abs(old_axg - axg) > 0.01:
                    df_master.loc[idx, "HXG"] = hxg
                    df_master.loc[idx, "AXG"] = axg
                    updated_count += 1
            else:
                pass
                
    print(f"\nUpdated xG for {updated_count} matches.")
    print("Saving back to CSV...")
    df_master.to_csv(MAIN_DATASET_PATH, index=False)
    print("Done!")

if __name__ == "__main__":
    run()
