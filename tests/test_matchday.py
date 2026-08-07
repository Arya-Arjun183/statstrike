import pytest
import pandas as pd
from premier_league_predictor.matchday import (
    compute_quick_facts,
    compute_model_explainability,
    get_matchday_overview,
)
from premier_league_predictor.data import load_matches

def test_compute_quick_facts():
    df = load_matches("data/raw/premier/epl-xg-data2014-26.csv")
    facts = compute_quick_facts("Arsenal", "Chelsea", df)
    
    assert "home_form" in facts
    assert "away_form" in facts
    assert "h2h" in facts
    assert "elo" in facts
    assert "home_split" in facts
    assert "away_split" in facts
    assert facts["elo"]["home_elo"] > 1000
    assert facts["elo"]["away_elo"] > 1000

def test_compute_model_explainability():
    df = load_matches("data/raw/premier/epl-xg-data2014-26.csv")
    facts = compute_quick_facts("Liverpool", "Man City", df)
    pred_result = {
        "home_team": "Liverpool",
        "away_team": "Man City",
        "prediction": "H",
        "prob_home": 0.48,
        "prob_draw": 0.28,
        "prob_away": 0.24,
    }
    explanation = compute_model_explainability("Liverpool", "Man City", pred_result, facts)
    
    assert "lambda_home" in explanation
    assert "lambda_away" in explanation
    assert "top_scores" in explanation
    assert len(explanation["top_scores"]) > 0
    assert "narrative" in explanation
    assert len(explanation["narrative"]) > 20
    assert "tactical_ratings" in explanation

def test_get_matchday_overview():
    overview = get_matchday_overview()
    assert overview["round"] == "Gameweek 1"
    assert overview["total_fixtures"] == 10
    assert len(overview["matches"]) == 10
    assert "summary" in overview
    assert overview["summary"]["predicted_home_wins"] >= 0
