from __future__ import annotations

import argparse

import pandas as pd

from premier_league_predictor.config import load_config
from premier_league_predictor.evaluation import evaluate_from_config
from premier_league_predictor.prediction import predict_fixtures, print_predictions
from premier_league_predictor.training import train_from_config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Premier League predictor CLI")
    sub = parser.add_subparsers(dest="command")

    # --- train ---
    train_p = sub.add_parser("train", help="Train a model")
    train_p.add_argument("--config", required=True, help="Path to YAML config")

    # --- evaluate ---
    eval_p = sub.add_parser("evaluate", help="Evaluate a trained model")
    eval_p.add_argument("--config", required=True, help="Path to YAML config")

    # --- serve ---
    serve_p = sub.add_parser("serve", help="Start the FastAPI prediction server")
    serve_p.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    serve_p.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve_p.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")

    # --- update-data ---
    update_p = sub.add_parser("update-data", help="Download free weekly match data and retrain")
    update_p.add_argument("--season", default="2526", help="Season code (e.g. 2526 or 2627)")
    update_p.add_argument("--retrain", action="store_true", default=True, help="Retrain model after update")

    # --- ingest-weekly ---
    ingest_p = sub.add_parser("ingest-weekly", help="Ingest a custom CSV file of weekly match results")
    ingest_p.add_argument("--file", required=True, help="Path to weekly CSV")
    ingest_p.add_argument("--season", default="2026-2027", help="Season name (e.g. 2026-2027)")
    ingest_p.add_argument("--retrain", action="store_true", default=True, help="Retrain model after ingest")

    # --- fetch-understat ---
    understat_p = sub.add_parser("fetch-understat", help="Fetch open Understat match & xG data and retrain")
    understat_p.add_argument("--season", default="2025", help="Season starting year (e.g. 2025 or 2026)")
    understat_p.add_argument("--retrain", action="store_true", default=True, help="Retrain model after fetch")

    # --- predict ---
    pred_p = sub.add_parser("predict", help="Predict upcoming match outcomes")
    pred_p.add_argument("--config", required=True, help="Path to YAML config")

    # Single-match mode
    pred_p.add_argument("--date", help="Match date (e.g. 16/08/2026)")
    pred_p.add_argument("--home", help="Home team name")
    pred_p.add_argument("--away", help="Away team name")
    pred_p.add_argument("--odds-h", type=float, help="B365 home odds (e.g. 1.85)")
    pred_p.add_argument("--odds-d", type=float, help="B365 draw odds (e.g. 3.60)")
    pred_p.add_argument("--odds-a", type=float, help="B365 away odds (e.g. 4.50)")

    # Batch mode
    pred_p.add_argument(
        "--fixtures",
        help="Path to CSV with upcoming fixtures (Date, HomeTeam, AwayTeam, ...)",
    )

    # --- precompute-cache ---
    cache_p = sub.add_parser("precompute-cache", help="Precompute prediction caches for the whole season")

    return parser


def _run_predict(args, config: dict) -> None:
    """Handle the predict sub-command."""
    fixtures: list[dict] = []

    if args.fixtures:
        # Batch mode – read fixtures from CSV
        fix_df = pd.read_csv(args.fixtures)
        results = predict_fixtures(config, fix_df)
    elif args.date and args.home and args.away:
        # Single-match mode
        fixture: dict = {
            "Date": args.date,
            "HomeTeam": args.home,
            "AwayTeam": args.away,
        }
        if args.odds_h and args.odds_d and args.odds_a:
            fixture["B365H"] = args.odds_h
            fixture["B365D"] = args.odds_d
            fixture["B365A"] = args.odds_a
        fixtures.append(fixture)
        results = predict_fixtures(config, fixtures)
    else:
        print("Error: provide either --fixtures CSV or --date/--home/--away")
        return

    print_predictions(results)


def main() -> None:
    args = _build_parser().parse_args()
    if not args.command:
        _build_parser().print_help()
        return

    if args.command == "serve":
        import uvicorn
        uvicorn.run("premier_league_predictor.server:app", host=args.host, port=args.port, reload=args.reload)
        return

    if args.command == "update-data":
        from premier_league_predictor.data_updater import download_football_data_season, update_and_retrain
        download_football_data_season(args.season)
        if args.retrain:
            update_and_retrain()
        return

    if args.command == "ingest-weekly":
        from premier_league_predictor.data_updater import ingest_weekly_csv, update_and_retrain
        added = ingest_weekly_csv(args.file, args.season)
        if added > 0 and args.retrain:
            update_and_retrain()
        return

    if args.command == "fetch-understat":
        from premier_league_predictor.data_updater import fetch_understat_season, update_and_retrain
        added = fetch_understat_season(args.season)
        if added > 0 and args.retrain:
            update_and_retrain()
        return

    if args.command == "precompute-cache":
        from premier_league_predictor.matchday import precompute_season_cache
        precompute_season_cache()
        return

    config = load_config(args.config)

    if args.command == "train":
        metrics = train_from_config(config)
        print(f"accuracy={metrics['accuracy']:.4f}")
        if "log_loss" in metrics:
            print(f"log_loss={metrics['log_loss']:.4f}")
        if "brier_score" in metrics:
            print(f"brier_score={metrics['brier_score']:.4f}")
    elif args.command == "evaluate":
        metrics = evaluate_from_config(config)
        print(f"accuracy={metrics['accuracy']:.4f}")
        if "log_loss" in metrics:
            print(f"log_loss={metrics['log_loss']:.4f}")
        if "brier_score" in metrics:
            print(f"brier_score={metrics['brier_score']:.4f}")
    elif args.command == "predict":
        _run_predict(args, config)


if __name__ == "__main__":
    main()
