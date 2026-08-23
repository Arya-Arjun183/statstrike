#!/usr/bin/env -S .venv/bin/python3
import json
import glob
from pathlib import Path
import csv
import sys

def main():
    import json
    import glob
    from pathlib import Path
    import csv
    import sys
    import os
    
    sys.path.append(os.path.abspath("src"))
    from premier_league_predictor.matchday import _inject_completed_status
    from premier_league_predictor.data import load_matches
    from premier_league_predictor.config import load_config
    
    config = load_config("configs/default.yaml")
    df_history = load_matches(csv_path=config["data"].get("csv_path"), csv_glob=config["data"].get("csv_glob"))

    cache_dir = Path("data/cache")
    if not cache_dir.exists():
        print("Error: data/cache directory not found.")
        sys.exit(1)

    json_files = glob.glob(str(cache_dir / "matchweek_*.json"))
    
    completed_matches = []
    
    print("Parsing cached predictions...")
    for f_path in json_files:
        try:
            with open(f_path, "r") as f:
                data = json.load(f)
                
            matches = data.get("matches", [])
            _inject_completed_status(matches, df_history)
            
            for m in matches:
                # Only evaluate matches that are completed AND have actual probabilities 
                # (to skip matches that were completed before the cache was ever generated)
                if m.get("status") == "completed" and m.get("actual_score"):
                    if m.get("prob_home", 0.0) == 0.0 and m.get("prob_draw", 0.0) == 0.0:
                        continue
                    completed_matches.append(m)
        except Exception as e:
            print(f"Warning: Failed to process {f_path}: {e}")

    if not completed_matches:
        print("No completed matches found in the cache. Run predictions on a completed matchweek first.")
        sys.exit(0)

    total_matches = len(completed_matches)
    correct_predictions = 0
    correct_exact_scores = 0
    total_brier_score = 0.0

    output_rows = []

    for m in completed_matches:
        actual_score = m["actual_score"]
        try:
            h_g_str, a_g_str = actual_score.split("-")
            h_g = int(h_g_str)
            a_g = int(a_g_str)
        except ValueError:
            print(f"Warning: Invalid actual_score format '{actual_score}' for match {m['fixture_id']}")
            continue

        if h_g > a_g:
            actual_outcome = 'H'
            true_probs = {'H': 1.0, 'D': 0.0, 'A': 0.0}
        elif h_g == a_g:
            actual_outcome = 'D'
            true_probs = {'H': 0.0, 'D': 1.0, 'A': 0.0}
        else:
            actual_outcome = 'A'
            true_probs = {'H': 0.0, 'D': 0.0, 'A': 1.0}

        prediction = m.get("prediction", "H")
        most_likely_score = m.get("most_likely_score", "")
        
        is_correct = (prediction == actual_outcome)
        is_exact_score = (most_likely_score == actual_score)

        if is_correct:
            correct_predictions += 1
        if is_exact_score:
            correct_exact_scores += 1

        p_home = m.get("prob_home", 0.0)
        p_draw = m.get("prob_draw", 0.0)
        p_away = m.get("prob_away", 0.0)

        # Brier Score for multi-class classification
        brier_loss = (p_home - true_probs['H'])**2 + \
                     (p_draw - true_probs['D'])**2 + \
                     (p_away - true_probs['A'])**2
        total_brier_score += brier_loss

        output_rows.append({
            "fixture_id": m.get("fixture_id"),
            "date": m.get("date"),
            "home_team": m.get("home_team"),
            "away_team": m.get("away_team"),
            "predicted_outcome": prediction,
            "predicted_score": most_likely_score,
            "actual_outcome": actual_outcome,
            "actual_score": actual_score,
            "prob_home": p_home,
            "prob_draw": p_draw,
            "prob_away": p_away,
            "is_correct_outcome": int(is_correct),
            "is_correct_exact_score": int(is_exact_score),
            "brier_score": round(brier_loss, 4)
        })

    # Sort output chronologically if possible, fallback to fixture_id
    output_rows.sort(key=lambda x: x["fixture_id"])

    # Calculate aggregations
    avg_accuracy = (correct_predictions / total_matches) * 100
    avg_exact_score = (correct_exact_scores / total_matches) * 100
    avg_brier = total_brier_score / total_matches

    # Print Summary
    print("=========================================")
    print("🏆 StatStrike Model Accuracy Tracker")
    print("=========================================")
    print(f"Total Completed Matches Tracked : {total_matches}")
    print(f"Overall W/D/L Accuracy          : {avg_accuracy:.2f}% ({correct_predictions}/{total_matches})")
    print(f"Exact Score Prediction Accuracy : {avg_exact_score:.2f}% ({correct_exact_scores}/{total_matches})")
    print(f"Average Brier Score (lower=better): {avg_brier:.4f}")
    print("=========================================")

    # Write CSV
    output_csv_path = Path("data/accuracy_tracking.csv")
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        "fixture_id", "date", "home_team", "away_team",
        "predicted_outcome", "predicted_score", "actual_outcome", "actual_score",
        "prob_home", "prob_draw", "prob_away",
        "is_correct_outcome", "is_correct_exact_score", "brier_score"
    ]
    
    with open(output_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            writer.writerow(row)
            
    print(f"✅ Detailed tracking saved to: {output_csv_path}")

if __name__ == "__main__":
    main()
