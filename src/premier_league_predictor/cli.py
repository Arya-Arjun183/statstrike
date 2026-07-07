from __future__ import annotations

import argparse

from premier_league_predictor.config import load_config
from premier_league_predictor.evaluation import evaluate_from_config
from premier_league_predictor.training import train_from_config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Premier League predictor CLI")
    parser.add_argument("command", choices=["train", "evaluate"])
    parser.add_argument("--config", required=True, help="Path to YAML config")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    config = load_config(args.config)

    if args.command == "train":
        metrics = train_from_config(config)
    else:
        metrics = evaluate_from_config(config)

    print(f"accuracy={metrics['accuracy']:.4f}")
    if "log_loss" in metrics:
        print(f"log_loss={metrics['log_loss']:.4f}")
    if "brier_score" in metrics:
        print(f"brier_score={metrics['brier_score']:.4f}")


if __name__ == "__main__":
    main()
