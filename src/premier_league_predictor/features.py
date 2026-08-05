from __future__ import annotations

from collections import deque

import pandas as pd

REQUIRED_COLUMNS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
BOOKMAKER_COLUMNS = ["B365H", "B365D", "B365A"]
SHOT_COLUMNS = ["HS", "AS", "HST", "AST"]
DISCIPLINE_COLUMNS = ["HF", "AF", "HY", "AY", "HR", "AR"]
CORNER_COLUMNS = ["HC", "AC"]
HALFTIME_COLUMNS = ["HTHG", "HTAG"]
CLOSING_ODDS_B365 = ["B365CH", "B365CD", "B365CA"]
CLOSING_ODDS_PS = ["PSCH", "PSCD", "PSCA"]
MULTI_BOOKMAKER_GROUPS = [
    ("B365H", "B365D", "B365A"),
    ("PSH", "PSD", "PSA"),
    ("BWH", "BWD", "BWA"),
]
AVG_ODDS_COLUMNS = ["AvgH", "AvgD", "AvgA"]
BB_AVG_ODDS_COLUMNS = ["BbAvH", "BbAvD", "BbAvA"]


def validate_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _safe_rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator > 0 else 0.0


def _rolling_average(values: deque[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _recency_weighted_average(values: deque[float], decay: float = 0.85) -> float:
    """Exponential-decay weighted average giving more weight to recent matches."""
    if not values:
        return 0.0
    n = len(values)
    weights = [decay ** (n - 1 - i) for i in range(n)]
    total_weight = sum(weights)
    return float(sum(v * w for v, w in zip(values, weights)) / total_weight)


def _rest_days(current_date: pd.Timestamp, last_date: pd.Timestamp | None) -> float:
    if pd.isna(current_date) or last_date is None or pd.isna(last_date):
        return 7.0
    return float(max((current_date - last_date).days, 0))


def _fixture_congestion(
    current_date: pd.Timestamp, recent_dates: deque, days: int
) -> int:
    """Count how many matches a team played in the last *days* days."""
    if pd.isna(current_date) or not recent_dates:
        return 0
    cutoff = current_date - pd.Timedelta(days=days)
    return sum(1 for d in recent_dates if d >= cutoff)


def _init_team_stats(has_discipline: bool, has_corners: bool, has_halftime: bool, has_xg_actual: bool = False) -> dict:
    """Create a fresh team-stats accumulator dictionary."""
    stats: dict = {
        "played": 0.0,
        "points": 0.0,
        "gf": 0.0,
        "ga": 0.0,
        # Multi-window rolling form (overall)
        "last3_all": deque(maxlen=3),
        "last5_all": deque(maxlen=5),
        "last10_all": deque(maxlen=10),
        # Home/away split rolling form
        "last3_home": deque(maxlen=3),
        "last5_home": deque(maxlen=5),
        "last10_home": deque(maxlen=10),
        "last3_away": deque(maxlen=3),
        "last5_away": deque(maxlen=5),
        "last10_away": deque(maxlen=10),
        # Rolling attacking/defensive
        "last5_gf": deque(maxlen=5),
        "last5_ga": deque(maxlen=5),
        # Opponent-adjusted form
        "last5_opp_adj": deque(maxlen=5),
        # Fixture congestion
        "recent_dates": deque(maxlen=20),
        "last_date": None,
        # Shots (season-to-date)
        "shots": 0.0,
        "sot": 0.0,
        "shots_allowed": 0.0,
        "sot_allowed": 0.0,
    }
    if has_discipline:
        stats["last5_fouls"] = deque(maxlen=5)
        stats["last5_yellows"] = deque(maxlen=5)
        stats["last5_reds"] = deque(maxlen=5)
        stats["last5_fouls_against"] = deque(maxlen=5)
    if has_corners:
        stats["last5_corners"] = deque(maxlen=5)
        stats["last5_corners_against"] = deque(maxlen=5)
    if has_halftime:
        stats["last5_ht_gf"] = deque(maxlen=5)
        stats["last5_ht_ga"] = deque(maxlen=5)
    if has_xg_actual:
        stats["last5_xg_for"] = deque(maxlen=5)
        stats["last5_xg_against"] = deque(maxlen=5)
    return stats


# ------------------------------------------------------------------
# Core row-by-row feature builder
# ------------------------------------------------------------------

def _build_pre_match_stats(  # noqa: C901 – unavoidable complexity
    df: pd.DataFrame,
    *,
    include_rest_days: bool,
    include_xg_proxy: bool,
    include_elo: bool,
    include_multi_window: bool,
    include_discipline: bool,
    include_fixture_congestion: bool,
    include_halftime: bool,
    include_opponent_adj: bool,
    include_xg_actual: bool,
    freeze_idx: int | None = None,
) -> pd.DataFrame:
    """Build pre-match features row-by-row.

    If *freeze_idx* is set, rows at index >= freeze_idx still get their
    features computed (using accumulated history) but do **not** update
    any accumulators afterwards.  This is used for prediction rows so
    that multiple upcoming fixtures all see the same historical state.
    """
    team_stats: dict[str, dict] = {}
    elo_ratings: dict[str, float] = {}
    rows: list[dict[str, float]] = []

    has_shot_data = include_xg_proxy and set(SHOT_COLUMNS).issubset(df.columns)
    has_discipline = include_discipline and set(DISCIPLINE_COLUMNS).issubset(df.columns)
    has_corners = include_discipline and set(CORNER_COLUMNS).issubset(df.columns)
    has_halftime = include_halftime and set(HALFTIME_COLUMNS).issubset(df.columns)
    has_xg_actual = include_xg_actual and set(["HXG", "AXG"]).issubset(df.columns)

    for row_idx, row in enumerate(df.itertuples(index=False)):
        match_date = row.Date
        home_team = str(row.HomeTeam)
        away_team = str(row.AwayTeam)

        home = team_stats.setdefault(
            home_team,
            _init_team_stats(has_discipline, has_corners, has_halftime, has_xg_actual=has_xg_actual),
        )
        away = team_stats.setdefault(
            away_team,
            _init_team_stats(has_discipline, has_corners, has_halftime, has_xg_actual=has_xg_actual),
        )

        # ---------- PRE-MATCH: Elo ----------
        home_elo = float(elo_ratings.get(home_team, 1500.0))
        away_elo = float(elo_ratings.get(away_team, 1500.0))

        # ---------- PRE-MATCH: Season-to-date ----------
        home_played = float(home["played"])
        away_played = float(away["played"])
        home_ppg = _safe_rate(float(home["points"]), home_played)
        away_ppg = _safe_rate(float(away["points"]), away_played)
        home_gf_pg = _safe_rate(float(home["gf"]), home_played)
        away_gf_pg = _safe_rate(float(away["gf"]), away_played)
        home_ga_pg = _safe_rate(float(home["ga"]), home_played)
        away_ga_pg = _safe_rate(float(away["ga"]), away_played)

        # ---------- PRE-MATCH: Last-5 form (always computed) ----------
        home_last5_ppg = _rolling_average(home["last5_all"])
        away_last5_ppg = _rolling_average(away["last5_all"])
        home_home_last5_ppg = _rolling_average(home["last5_home"])
        away_away_last5_ppg = _rolling_average(away["last5_away"])

        row_features: dict[str, float] = {
            "home_matches_played": home_played,
            "away_matches_played": away_played,
            "home_ppg": home_ppg,
            "away_ppg": away_ppg,
            "ppg_diff": home_ppg - away_ppg,
            "home_gf_pg": home_gf_pg,
            "away_gf_pg": away_gf_pg,
            "home_ga_pg": home_ga_pg,
            "away_ga_pg": away_ga_pg,
            "gf_pg_diff": home_gf_pg - away_gf_pg,
            "ga_pg_diff": home_ga_pg - away_ga_pg,
            "home_last5_ppg": home_last5_ppg,
            "away_last5_ppg": away_last5_ppg,
            "last5_ppg_diff": home_last5_ppg - away_last5_ppg,
            "home_home_last5_ppg": home_home_last5_ppg,
            "away_away_last5_ppg": away_away_last5_ppg,
            "home_away_form_diff": home_home_last5_ppg - away_away_last5_ppg,
        }

        # ---------- PRE-MATCH: Multi-window rolling ----------
        if include_multi_window:
            h3 = _rolling_average(home["last3_all"])
            a3 = _rolling_average(away["last3_all"])
            h10 = _rolling_average(home["last10_all"])
            a10 = _rolling_average(away["last10_all"])
            h10_rw = _recency_weighted_average(home["last10_all"])
            a10_rw = _recency_weighted_average(away["last10_all"])

            row_features["home_last3_ppg"] = h3
            row_features["away_last3_ppg"] = a3
            row_features["last3_ppg_diff"] = h3 - a3
            row_features["home_last10_ppg"] = h10
            row_features["away_last10_ppg"] = a10
            row_features["last10_ppg_diff"] = h10 - a10
            # Momentum: short-term minus long-term
            row_features["home_momentum"] = h3 - h10
            row_features["away_momentum"] = a3 - a10
            row_features["momentum_diff"] = (h3 - h10) - (a3 - a10)
            # Recency-weighted last-10
            row_features["home_last10_rw"] = h10_rw
            row_features["away_last10_rw"] = a10_rw
            row_features["last10_rw_diff"] = h10_rw - a10_rw
            # Home/away specific multi-window
            row_features["home_home_last3_ppg"] = _rolling_average(home["last3_home"])
            row_features["away_away_last3_ppg"] = _rolling_average(away["last3_away"])
            row_features["home_home_last10_ppg"] = _rolling_average(home["last10_home"])
            row_features["away_away_last10_ppg"] = _rolling_average(away["last10_away"])

        # ---------- PRE-MATCH: Rolling attacking/defensive form ----------
        h_rgf = _rolling_average(home["last5_gf"])
        a_rgf = _rolling_average(away["last5_gf"])
        h_rga = _rolling_average(home["last5_ga"])
        a_rga = _rolling_average(away["last5_ga"])
        row_features["home_rolling_gf"] = h_rgf
        row_features["away_rolling_gf"] = a_rgf
        row_features["rolling_gf_diff"] = h_rgf - a_rgf
        row_features["home_rolling_ga"] = h_rga
        row_features["away_rolling_ga"] = a_rga
        row_features["rolling_ga_diff"] = h_rga - a_rga

        # ---------- PRE-MATCH: Opponent-adjusted form ----------
        if include_opponent_adj:
            h_oa = _rolling_average(home["last5_opp_adj"])
            a_oa = _rolling_average(away["last5_opp_adj"])
            row_features["home_opp_adj_form"] = h_oa
            row_features["away_opp_adj_form"] = a_oa
            row_features["opp_adj_form_diff"] = h_oa - a_oa

        # ---------- PRE-MATCH: Elo features ----------
        if include_elo:
            row_features["home_elo"] = home_elo
            row_features["away_elo"] = away_elo
            row_features["elo_diff"] = home_elo - away_elo

        # ---------- PRE-MATCH: xG proxy ----------
        if has_shot_data:
            h_spg = _safe_rate(float(home["shots"]), home_played)
            a_spg = _safe_rate(float(away["shots"]), away_played)
            h_sotpg = _safe_rate(float(home["sot"]), home_played)
            a_sotpg = _safe_rate(float(away["sot"]), away_played)
            h_sa_pg = _safe_rate(float(home["shots_allowed"]), home_played)
            a_sa_pg = _safe_rate(float(away["shots_allowed"]), away_played)
            h_sota_pg = _safe_rate(float(home["sot_allowed"]), home_played)
            a_sota_pg = _safe_rate(float(away["sot_allowed"]), away_played)

            h_xg_f = 0.1 * h_sotpg + 0.03 * max(h_spg - h_sotpg, 0.0)
            a_xg_f = 0.1 * a_sotpg + 0.03 * max(a_spg - a_sotpg, 0.0)
            h_xg_a = 0.1 * h_sota_pg + 0.03 * max(h_sa_pg - h_sota_pg, 0.0)
            a_xg_a = 0.1 * a_sota_pg + 0.03 * max(a_sa_pg - a_sota_pg, 0.0)

            row_features["home_xg_proxy_for"] = h_xg_f
            row_features["away_xg_proxy_for"] = a_xg_f
            row_features["xg_proxy_for_diff"] = h_xg_f - a_xg_f
            row_features["home_xg_proxy_against"] = h_xg_a
            row_features["away_xg_proxy_against"] = a_xg_a
            row_features["xg_proxy_against_diff"] = h_xg_a - a_xg_a

        # ---------- PRE-MATCH: Rest days ----------
        if include_rest_days:
            h_rest = _rest_days(match_date, home["last_date"])
            a_rest = _rest_days(match_date, away["last_date"])
            row_features["home_rest_days"] = h_rest
            row_features["away_rest_days"] = a_rest
            row_features["rest_days_diff"] = h_rest - a_rest

        # ---------- PRE-MATCH: Fixture congestion ----------
        if include_fixture_congestion:
            h7 = float(_fixture_congestion(match_date, home["recent_dates"], 7))
            a7 = float(_fixture_congestion(match_date, away["recent_dates"], 7))
            h14 = float(_fixture_congestion(match_date, home["recent_dates"], 14))
            a14 = float(_fixture_congestion(match_date, away["recent_dates"], 14))
            row_features["home_matches_7d"] = h7
            row_features["away_matches_7d"] = a7
            row_features["congestion_7d_diff"] = h7 - a7
            row_features["home_matches_14d"] = h14
            row_features["away_matches_14d"] = a14
            row_features["congestion_14d_diff"] = h14 - a14

        # ---------- PRE-MATCH: Discipline ----------
        if has_discipline:
            row_features["home_fouls_pg"] = _rolling_average(home["last5_fouls"])
            row_features["away_fouls_pg"] = _rolling_average(away["last5_fouls"])
            row_features["fouls_diff"] = row_features["home_fouls_pg"] - row_features["away_fouls_pg"]
            row_features["home_yellows_pg"] = _rolling_average(home["last5_yellows"])
            row_features["away_yellows_pg"] = _rolling_average(away["last5_yellows"])
            row_features["home_reds_pg"] = _rolling_average(home["last5_reds"])
            row_features["away_reds_pg"] = _rolling_average(away["last5_reds"])

        if has_corners:
            h_cpg = _rolling_average(home["last5_corners"])
            a_cpg = _rolling_average(away["last5_corners"])
            row_features["home_corners_pg"] = h_cpg
            row_features["away_corners_pg"] = a_cpg
            row_features["corners_diff"] = h_cpg - a_cpg
            row_features["home_corners_against_pg"] = _rolling_average(home["last5_corners_against"])
            row_features["away_corners_against_pg"] = _rolling_average(away["last5_corners_against"])

        # ---------- PRE-MATCH: Half-time tendency ----------
        if has_halftime:
            h_ht_gf = _rolling_average(home["last5_ht_gf"])
            a_ht_gf = _rolling_average(away["last5_ht_gf"])
            h_ht_ga = _rolling_average(home["last5_ht_ga"])
            a_ht_ga = _rolling_average(away["last5_ht_ga"])
            h_ft_gf = _rolling_average(home["last5_gf"])
            a_ft_gf = _rolling_average(away["last5_gf"])
            row_features["home_first_half_ratio"] = _safe_rate(h_ht_gf, h_ft_gf)
            row_features["away_first_half_ratio"] = _safe_rate(a_ht_gf, a_ft_gf)
            row_features["home_ht_gf_pg"] = h_ht_gf
            row_features["away_ht_gf_pg"] = a_ht_gf
            row_features["home_ht_ga_pg"] = h_ht_ga
            row_features["away_ht_ga_pg"] = a_ht_ga

        # ---------- PRE-MATCH: Actual xG rolling form ----------
        if has_xg_actual:
            h_xgf = _rolling_average(home["last5_xg_for"])
            a_xgf = _rolling_average(away["last5_xg_for"])
            h_xga = _rolling_average(home["last5_xg_against"])
            a_xga = _rolling_average(away["last5_xg_against"])
            row_features["home_xg_for_pg"] = h_xgf
            row_features["away_xg_for_pg"] = a_xgf
            row_features["xg_for_diff"] = h_xgf - a_xgf
            row_features["home_xg_against_pg"] = h_xga
            row_features["away_xg_against_pg"] = a_xga
            row_features["xg_against_diff"] = h_xga - a_xga

        rows.append(row_features)

        # ===================================================================
        # POST-MATCH UPDATES — update accumulators after feature extraction
        # Skip updates for prediction rows (at or beyond freeze_idx).
        # ===================================================================
        if freeze_idx is not None and row_idx >= freeze_idx:
            continue

        fthg = float(row.FTHG)
        ftag = float(row.FTAG)
        result = str(row.FTR)

        home_points = 3.0 if result == "H" else 1.0 if result == "D" else 0.0
        away_points = 3.0 if result == "A" else 1.0 if result == "D" else 0.0

        # Season-to-date totals
        home["played"] = float(home["played"]) + 1.0
        home["points"] = float(home["points"]) + home_points
        home["gf"] = float(home["gf"]) + fthg
        home["ga"] = float(home["ga"]) + ftag

        away["played"] = float(away["played"]) + 1.0
        away["points"] = float(away["points"]) + away_points
        away["gf"] = float(away["gf"]) + ftag
        away["ga"] = float(away["ga"]) + fthg

        # Multi-window rolling form
        home["last3_all"].append(home_points)
        home["last5_all"].append(home_points)
        home["last10_all"].append(home_points)
        home["last3_home"].append(home_points)
        home["last5_home"].append(home_points)
        home["last10_home"].append(home_points)

        away["last3_all"].append(away_points)
        away["last5_all"].append(away_points)
        away["last10_all"].append(away_points)
        away["last3_away"].append(away_points)
        away["last5_away"].append(away_points)
        away["last10_away"].append(away_points)

        # Rolling attacking/defensive
        home["last5_gf"].append(fthg)
        home["last5_ga"].append(ftag)
        away["last5_gf"].append(ftag)
        away["last5_ga"].append(fthg)

        # Opponent-adjusted form
        if include_opponent_adj:
            home["last5_opp_adj"].append(home_points * (away_elo / 1500.0))
            away["last5_opp_adj"].append(away_points * (home_elo / 1500.0))

        # Dates
        home["last_date"] = match_date
        away["last_date"] = match_date
        if not pd.isna(match_date):
            home["recent_dates"].append(match_date)
            away["recent_dates"].append(match_date)

        # Shot accumulators
        if has_shot_data:
            hs = float(getattr(row, "HS"))
            a_s = float(getattr(row, "AS"))
            hst = float(getattr(row, "HST"))
            ast_val = float(getattr(row, "AST"))

            home["shots"] = float(home["shots"]) + hs
            home["sot"] = float(home["sot"]) + hst
            home["shots_allowed"] = float(home["shots_allowed"]) + a_s
            home["sot_allowed"] = float(home["sot_allowed"]) + ast_val

            away["shots"] = float(away["shots"]) + a_s
            away["sot"] = float(away["sot"]) + ast_val
            away["shots_allowed"] = float(away["shots_allowed"]) + hs
            away["sot_allowed"] = float(away["sot_allowed"]) + hst

        # Elo update (independent of shot data — bug fix)
        if include_elo:
            home_expected = 1.0 / (1.0 + 10 ** ((away_elo - (home_elo + 65.0)) / 400.0))
            away_expected = 1.0 - home_expected
            actual_home = 1.0 if result == "H" else 0.5 if result == "D" else 0.0
            actual_away = 1.0 if result == "A" else 0.5 if result == "D" else 0.0
            k_factor = 20.0
            elo_ratings[home_team] = home_elo + k_factor * (actual_home - home_expected)
            elo_ratings[away_team] = away_elo + k_factor * (actual_away - away_expected)

        # Discipline accumulators
        if has_discipline:
            home["last5_fouls"].append(float(getattr(row, "HF")))
            home["last5_yellows"].append(float(getattr(row, "HY")))
            home["last5_reds"].append(float(getattr(row, "HR")))
            away["last5_fouls"].append(float(getattr(row, "AF")))
            away["last5_yellows"].append(float(getattr(row, "AY")))
            away["last5_reds"].append(float(getattr(row, "AR")))
            home["last5_fouls_against"].append(float(getattr(row, "AF")))
            away["last5_fouls_against"].append(float(getattr(row, "HF")))

        if has_corners:
            home["last5_corners"].append(float(getattr(row, "HC")))
            away["last5_corners"].append(float(getattr(row, "AC")))
            home["last5_corners_against"].append(float(getattr(row, "AC")))
            away["last5_corners_against"].append(float(getattr(row, "HC")))

        # Half-time accumulators
        if has_halftime:
            home["last5_ht_gf"].append(float(getattr(row, "HTHG")))
            home["last5_ht_ga"].append(float(getattr(row, "HTAG")))
            away["last5_ht_gf"].append(float(getattr(row, "HTAG")))
            away["last5_ht_ga"].append(float(getattr(row, "HTHG")))

        # Actual xG accumulators
        if has_xg_actual:
            hxg = float(getattr(row, "HXG"))
            axg = float(getattr(row, "AXG"))
            home["last5_xg_for"].append(hxg)
            home["last5_xg_against"].append(axg)
            away["last5_xg_for"].append(axg)
            away["last5_xg_against"].append(hxg)

    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# Bookmaker / odds helpers
# ------------------------------------------------------------------

def _implied_prob(odds: pd.Series) -> pd.Series:
    """Convert decimal odds to raw implied probability."""
    return 1.0 / odds


def _normalize_probs(
    h: pd.Series, d: pd.Series, a: pd.Series
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Remove overround from implied probabilities."""
    total = h + d + a
    return h / total, d / total, a / total


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def build_features(
    df: pd.DataFrame,
    *,
    include_rest_days: bool = True,
    include_xg_proxy: bool = True,
    include_elo: bool = True,
    include_multi_window: bool = True,
    include_discipline: bool = True,
    include_odds_movement: bool = True,
    include_multi_bookmaker: bool = True,
    include_fixture_congestion: bool = True,
    include_halftime: bool = True,
    include_opponent_adj: bool = True,
    include_xg_actual: bool = False,
    prediction_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build pre-match feature matrix and target labels from raw match data.

    Every feature is computed using only information available *before* the
    match kicks off, so there is no data leakage.  All boolean flags default
    to ``True`` so that the full feature set is used unless explicitly
    disabled.

    If *prediction_df* is provided, those rows are appended with dummy
    results.  Their features are computed from accumulated history but
    they do not update any accumulators (so multiple prediction rows all
    see the same historical state).
    """
    validate_columns(df)

    ordered_df = df.sort_values("Date").reset_index(drop=True).copy()
    ordered_df["Date"] = pd.to_datetime(ordered_df["Date"], dayfirst=True, errors="coerce")

    # Append prediction rows with dummy results.
    freeze_idx: int | None = None
    if prediction_df is not None:
        freeze_idx = len(ordered_df)
        pred = prediction_df.copy()
        pred["Date"] = pd.to_datetime(pred["Date"], dayfirst=True, errors="coerce")
        # Fill required result columns with dummies (never used).
        for col, default in (("FTHG", 0), ("FTAG", 0), ("FTR", "H")):
            if col not in pred.columns:
                pred[col] = default
        ordered_df = pd.concat([ordered_df, pred], ignore_index=True)

    feat = _build_pre_match_stats(
        ordered_df,
        include_rest_days=include_rest_days,
        include_xg_proxy=include_xg_proxy,
        include_elo=include_elo,
        include_multi_window=include_multi_window,
        include_discipline=include_discipline,
        include_fixture_congestion=include_fixture_congestion,
        include_halftime=include_halftime,
        include_opponent_adj=include_opponent_adj,
        include_xg_actual=include_xg_actual,
        freeze_idx=freeze_idx,
    )
    feat["is_weekend"] = ordered_df["Date"].dt.dayofweek.ge(5).astype(int)
    feat["home_team"] = ordered_df["HomeTeam"].astype(str)
    feat["away_team"] = ordered_df["AwayTeam"].astype(str)

    # Propagate season label so training code can split by season.
    if "season" in ordered_df.columns:
        feat["_season"] = ordered_df["season"].values

    # --- Opening bookmaker odds (Bet365) ---
    if set(BOOKMAKER_COLUMNS).issubset(ordered_df.columns):
        odds = ordered_df[BOOKMAKER_COLUMNS].apply(pd.to_numeric, errors="coerce")
        imp_h = _implied_prob(odds["B365H"])
        imp_d = _implied_prob(odds["B365D"])
        imp_a = _implied_prob(odds["B365A"])
        feat["imp_home_prob"], feat["imp_draw_prob"], feat["imp_away_prob"] = (
            _normalize_probs(imp_h, imp_d, imp_a)
        )

    # --- Odds movement (opening → closing) ---
    if include_odds_movement:
        close_cols: list[str] | None = None
        if set(CLOSING_ODDS_B365).issubset(ordered_df.columns):
            close_cols = CLOSING_ODDS_B365
        elif set(CLOSING_ODDS_PS).issubset(ordered_df.columns):
            close_cols = CLOSING_ODDS_PS

        if close_cols and "imp_home_prob" in feat.columns:
            co = ordered_df[close_cols].apply(pd.to_numeric, errors="coerce")
            c_h = _implied_prob(co[close_cols[0]])
            c_d = _implied_prob(co[close_cols[1]])
            c_a = _implied_prob(co[close_cols[2]])
            ch, cd, ca = _normalize_probs(c_h, c_d, c_a)
            feat["odds_drift_home"] = ch - feat["imp_home_prob"]
            feat["odds_drift_draw"] = cd - feat["imp_draw_prob"]
            feat["odds_drift_away"] = ca - feat["imp_away_prob"]

    # --- Multi-bookmaker consensus ---
    if include_multi_bookmaker:
        available_groups = [
            g for g in MULTI_BOOKMAKER_GROUPS if set(g).issubset(ordered_df.columns)
        ]
        if len(available_groups) >= 2:
            all_h, all_d, all_a = [], [], []
            for g in available_groups:
                go = ordered_df[list(g)].apply(pd.to_numeric, errors="coerce")
                gh = _implied_prob(go[g[0]])
                gd = _implied_prob(go[g[1]])
                ga = _implied_prob(go[g[2]])
                hn, dn, an = _normalize_probs(gh, gd, ga)
                all_h.append(hn)
                all_d.append(dn)
                all_a.append(an)
            imp_h_df = pd.concat(all_h, axis=1)
            imp_d_df = pd.concat(all_d, axis=1)
            imp_a_df = pd.concat(all_a, axis=1)
            feat["consensus_home_prob"] = imp_h_df.mean(axis=1)
            feat["consensus_draw_prob"] = imp_d_df.mean(axis=1)
            feat["consensus_away_prob"] = imp_a_df.mean(axis=1)
            feat["spread_home"] = imp_h_df.max(axis=1) - imp_h_df.min(axis=1)
            feat["spread_draw"] = imp_d_df.max(axis=1) - imp_d_df.min(axis=1)
            feat["spread_away"] = imp_a_df.max(axis=1) - imp_a_df.min(axis=1)

    for col in ["FTHG", "FTAG", "HXG", "AXG"]:
        if col in ordered_df.columns:
            feat[col] = ordered_df[col].values

    target = ordered_df["FTR"].astype(str)
    
    return feat, target
