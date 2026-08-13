from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Server starts up instantaneously using local dataset and trained models
    yield

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

class PredictionRequest(BaseModel):
    home_team: str
    away_team: str
    date: str

class MatchInsightsRequest(BaseModel):
    home_team: str
    away_team: str
    date: str = "15/08/2026"

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/matchday")
@app.get("/matchday")
def matchday(matchweek: int = Query(default=1, ge=1, le=38)):
    """Retrieve full matchday predictions, quick facts, and explainability."""
    try:
        return get_matchday_overview(matchweek=matchweek)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/match/insights")
@app.post("/match/insights")
def match_insights(request: MatchInsightsRequest):
    """Retrieve deep quick facts and explainability for any matchup."""
    try:
        config = load_config(CONFIG_PATH)
        fixtures = [{
            "HomeTeam": request.home_team,
            "AwayTeam": request.away_team,
            "Date": request.date,
        }]
        results = predict_fixtures(config, fixtures)
        if not results:
            raise HTTPException(status_code=400, detail="Prediction failed.")
        
        p_res = results[0]
        df_history = load_matches(
            csv_path=config["data"].get("csv_path"),
            csv_glob=config["data"].get("csv_glob")
        )
        quick_facts = compute_quick_facts(request.home_team, request.away_team, df_history)
        odds = get_match_odds(request.home_team, request.away_team)
        explanation = compute_model_explainability(request.home_team, request.away_team, p_res, quick_facts)
        
        return {
            "home_team": normalize_team_name(request.home_team),
            "away_team": normalize_team_name(request.away_team),
            "date": request.date,
            "prediction": p_res.get("prediction"),
            "prob_home": p_res.get("prob_home"),
            "prob_draw": p_res.get("prob_draw"),
            "prob_away": p_res.get("prob_away"),
            "quick_facts": quick_facts,
            "explanation": explanation,
            "odds": odds,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a sync with API-Football in the background."""
    background_tasks.add_task(sync_latest_data)
    return {"message": "Data sync scheduled"}

@app.post("/predict")
@app.post("/api/predict")
def predict(request: PredictionRequest):
    try:
        config = load_config(CONFIG_PATH)
        fixtures = [
            {
                "HomeTeam": request.home_team,
                "AwayTeam": request.away_team,
                "Date": request.date,
            }
        ]
        results = predict_fixtures(config, fixtures)
        if not results:
            raise HTTPException(status_code=400, detail="Prediction failed. Ensure model is trained and data is available.")
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



def start():
    """Start the uvicorn server."""
    import uvicorn
    uvicorn.run("premier_league_predictor.server:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()
