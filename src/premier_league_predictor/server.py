from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

from premier_league_predictor.config import load_config
from premier_league_predictor.prediction import predict_fixtures
from premier_league_predictor.api_football import sync_latest_data
from premier_league_predictor.matchday import (
    get_matchday_overview,
    compute_quick_facts,
    compute_model_explainability,
)
from premier_league_predictor.external_data import get_match_odds
from premier_league_predictor.data import load_matches, normalize_team_name

import joblib
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading models and dataset into memory...")
    config = load_config(CONFIG_PATH)
    
    df_history = load_matches(
        csv_path=config["data"].get("csv_path"),
        csv_glob=config["data"].get("csv_glob")
    )
    
    model_path = Path(config["output"]["model_path"])
    if model_path.exists():
        model = joblib.load(model_path)
    else:
        print("Warning: Model not found at", model_path)
        model = None

    app.state.config = config
    app.state.df_history = df_history
    app.state.model = model
    
    print("Startup complete.")
    yield
    print("Shutting down.")

app = FastAPI(title="Premier League Predictor API", lifespan=lifespan)

# Allow CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use the xG efficient configuration
CONFIG_PATH = "configs/test_xg_efficient.yaml"



@app.get("/health")
def health_check():
    return {"status": "ok"}

from typing import Optional

@app.get("/api/matchday")
@app.get("/matchday")
def matchday(request: Request, matchweek: Optional[int] = Query(default=None, ge=1, le=38)):
    """Retrieve full matchday predictions, quick facts, and explainability."""
    try:
        return get_matchday_overview(
            matchweek=matchweek,
            config=request.app.state.config,
            model=request.app.state.model,
            df_history=request.app.state.df_history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a sync with API-Football in the background."""
    background_tasks.add_task(sync_latest_data)
    return {"message": "Data sync scheduled"}





def start():
    """Start the uvicorn server."""
    import uvicorn
    uvicorn.run("premier_league_predictor.server:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()
