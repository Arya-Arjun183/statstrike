import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from premier_league_predictor.config import load_config
from premier_league_predictor.prediction import predict_fixtures

app = FastAPI(title="Premier League Predictor API")

# Allow CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use the best performing configuration
CONFIG_PATH = "configs/binary_home.yaml"

class PredictionRequest(BaseModel):
    home_team: str
    away_team: str
    date: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

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

@app.post("/upload")
async def upload_data(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    data_dir = Path("data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = data_dir / file.filename
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        return {"message": f"Successfully uploaded {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

def start():
    """Start the uvicorn server."""
    import uvicorn
    uvicorn.run("premier_league_predictor.server:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()
