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
