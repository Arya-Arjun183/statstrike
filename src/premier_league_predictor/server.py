from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from premier_league_predictor.config import load_config
from premier_league_predictor.prediction import predict_fixtures
from premier_league_predictor.api_football import sync_latest_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Attempt initial data sync on startup if API key is present
    try:
        sync_latest_data()
    except Exception as e:
        print(f"Initial sync warning: {e}")
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

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a sync with API-Football in the background."""
    background_tasks.add_task(sync_latest_data)
    return {"message": "Data sync scheduled"}

@app.post("/predict")
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
