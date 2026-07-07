import pandas as pd

from premier_league_predictor.features import build_features


def _make_sample_df(n: int = 4, include_shots: bool = True, include_discipline: bool = True, include_halftime: bool = True) -> pd.DataFrame:
    """Create a minimal multi-match sample DataFrame for testing."""
    data = {
        "Date": [f"2025-08-{10 + i}" for i in range(n)],
        "HomeTeam": ["Arsenal", "Liverpool", "Chelsea", "Everton"][:n],
        "AwayTeam": ["Chelsea", "Everton", "Arsenal", "Liverpool"][:n],
        "FTHG": [2, 1, 0, 3][:n],
        "FTAG": [1, 1, 2, 0][:n],
        "FTR": ["H", "D", "A", "H"][:n],
    }
    if include_shots:
        data.update({
            "HS": [12, 8, 10, 14][:n],
            "AS": [7, 9, 11, 5][:n],
            "HST": [5, 3, 4, 6][:n],
            "AST": [2, 4, 5, 2][:n],
        })
    if include_discipline:
        data.update({
            "HF": [10, 12, 9, 11][:n],
            "AF": [8, 10, 13, 7][:n],
            "HY": [2, 3, 1, 2][:n],
            "AY": [1, 2, 3, 1][:n],
            "HR": [0, 0, 1, 0][:n],
            "AR": [0, 1, 0, 0][:n],
            "HC": [6, 4, 5, 8][:n],
            "AC": [3, 5, 7, 2][:n],
        })
    if include_halftime:
        data.update({
            "HTHG": [1, 0, 0, 2][:n],
            "HTAG": [0, 1, 1, 0][:n],
        })
    return pd.DataFrame(data)


def test_build_features_outputs_expected_columns() -> None:
    df = _make_sample_df()

    x, y = build_features(df, include_rest_days=True, include_elo=True)

    # Core features
    assert {
        "home_matches_played",
        "away_matches_played",
        "home_ppg",
        "away_ppg",
        "ppg_diff",
        "home_last5_ppg",
        "away_last5_ppg",
        "last5_ppg_diff",
        "home_home_last5_ppg",
        "away_away_last5_ppg",
        "home_away_form_diff",
        "home_elo",
        "away_elo",
        "elo_diff",
        "home_rest_days",
        "away_rest_days",
        "rest_days_diff",
        "home_team",
        "away_team",
        "is_weekend",
    }.issubset(set(x.columns))

    # Multi-window features
    assert "home_last3_ppg" in x.columns
    assert "home_last10_ppg" in x.columns
    assert "home_momentum" in x.columns
    assert "home_last10_rw" in x.columns

    # Rolling attacking/defensive
    assert "home_rolling_gf" in x.columns
    assert "home_rolling_ga" in x.columns

    # Opponent-adjusted form
    assert "home_opp_adj_form" in x.columns
    assert "opp_adj_form_diff" in x.columns

    assert list(y) == ["H", "D", "A", "H"]


def test_build_features_discipline_columns() -> None:
    df = _make_sample_df()

    x, _ = build_features(df, include_discipline=True)

    assert "home_fouls_pg" in x.columns
    assert "away_fouls_pg" in x.columns
    assert "home_yellows_pg" in x.columns
    assert "home_corners_pg" in x.columns
    assert "corners_diff" in x.columns


def test_build_features_halftime_columns() -> None:
    df = _make_sample_df()

    x, _ = build_features(df, include_halftime=True)

    assert "home_first_half_ratio" in x.columns
    assert "home_ht_gf_pg" in x.columns
    assert "away_ht_ga_pg" in x.columns


def test_build_features_fixture_congestion() -> None:
    df = _make_sample_df()

    x, _ = build_features(df, include_fixture_congestion=True)

    assert "home_matches_7d" in x.columns
    assert "away_matches_14d" in x.columns
    assert "congestion_7d_diff" in x.columns


def test_build_features_can_disable_all_new_features() -> None:
    df = _make_sample_df(n=2, include_shots=False, include_discipline=False, include_halftime=False)

    x, _ = build_features(
        df,
        include_rest_days=False,
        include_elo=False,
        include_multi_window=False,
        include_discipline=False,
        include_fixture_congestion=False,
        include_halftime=False,
        include_opponent_adj=False,
        include_xg_proxy=False,
        include_odds_movement=False,
        include_multi_bookmaker=False,
    )

    # None of the optional features should be present
    assert "home_rest_days" not in x.columns
    assert "home_elo" not in x.columns
    assert "home_last3_ppg" not in x.columns
    assert "home_fouls_pg" not in x.columns
    assert "home_matches_7d" not in x.columns
    assert "home_ht_gf_pg" not in x.columns
    assert "home_opp_adj_form" not in x.columns
    assert "home_xg_proxy_for" not in x.columns

    # Core features should still be present
    assert "home_ppg" in x.columns
    assert "home_last5_ppg" in x.columns
    assert "home_rolling_gf" in x.columns


def test_recency_weighted_differs_from_simple() -> None:
    """Recency-weighted average should differ from simple average when values vary."""
    from premier_league_predictor.features import _recency_weighted_average, _rolling_average
    from collections import deque

    vals = deque([0.0, 0.0, 0.0, 3.0, 3.0], maxlen=10)
    simple = _rolling_average(vals)
    weighted = _recency_weighted_average(vals)

    # Weighted should be higher because recent values (3.0) get more weight
    assert weighted > simple
