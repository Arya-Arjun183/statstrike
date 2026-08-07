# StatStrike ⚡⚽

**StatStrike** is a modern, high-performance Premier League match outcome predictor and tactical analytics platform powered by Machine Learning and Expected Goals (xG) modeling.

![StatStrike Banner](frontend/public/favicon.svg)

---

## 🚀 Key Features

### 1. Matchday Hub & 2026/27 Gameweek Selector
- Complete **38-Gameweek calendar** for the 2026/27 Premier League season loaded from official fixtures (`data/raw/premier/fixtures-26-27.csv`).
- Real-time match prediction cards with probabilistic outcome breakdowns (**Home Win %**, **Draw %**, **Away Win %**).
- **Most Likely Scorelines** computed via Poisson & Dixon-Coles goal expectancy distributions.
- **Confidence Badges**: Filter matches by *High Confidence* or *Toss-Up / Value Draw* picks.

### 2. "Why" Tactical Explanations & Quick Facts Modal
Click on any fixture card to open a deep-dive tactical modal featuring:
- **Model Explainability**: Top positive and negative factors influencing the prediction (Rolling xG, Home Advantage, Defensive Momentum, Head-to-Head record).
- **Recent Form Tracker**: Last 5 matches for each side with exact scores, dates, and per-match xG creation vs. concession.
- **Promoted Teams Intelligence**: Automatic ingestion and calibration of EFL Championship 2025/26 data for newly promoted sides (**Coventry City**, **Hull City**, **Ipswich Town**).
- **Head-to-Head & Season Splits**: Historical win rates and goal averages at home vs. away.

### 3. Custom Match Simulator
- Test hypothetical or custom matchups between any Premier League teams on any date.
- Instant model inference returning simulated outcome probabilities, predicted scorelines, and tactical summaries.

### 4. Modern Glassmorphism UI
- Dynamic dark mode and light mode theming.
- Custom vector logo mark (**Integrated Slash Trajectory**) with micro-animations and glow aesthetics.
- Built with React 19, TypeScript, Vite, and Vanilla CSS.

---

## 🛠️ Architecture & ML Pipeline

### Models
- **Dixon-Coles Poisson Model**: Estimates bivariate goal distributions with low-score correlation adjustment ($\rho$) and team-specific attack/defense ratings.
- **CatBoost Classifier**: Gradient-boosted trees trained on rolling xG differentials, rest days, form trajectory, and home field advantage.
- **Ensemble Predictor**: Blends goal-based Poisson distributions with probabilistic classification for robust win/draw/loss calibration.

### Data Sources
- `data/raw/premier/epl-xg-data2014-26.csv`: Historical Premier League match and xG dataset (2014–2026).
- `data/raw/premier/fixtures-26-27.csv`: 2026/27 official Premier League schedule.
- `data/raw/premier/EFL_Championship_25_26_xG.csv`: 2025/26 Championship dataset with verified xG overrides for promoted clubs.

---

## 💻 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Clone & Environment Setup
```bash
# Clone the repository
git clone https://github.com/Arya-Arjun183/statstrike.git
cd statstrike

# Set up Python virtual environment & install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Install Frontend dependencies
cd frontend
npm install
cd ..
```

---

### 2. Running the Application

Open two terminal windows:

#### Terminal 1: Start Backend API (FastAPI)
```bash
./.venv/bin/uvicorn premier_league_predictor.server:app --reload --port 8000
```
*API will run on `http://localhost:8000` (Docs available at `http://localhost:8000/docs`)*

#### Terminal 2: Start Frontend (React + Vite)
```bash
cd frontend
npm run dev
```
*Frontend will run on `http://localhost:5173`*

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Server health check |
| `GET` | `/api/matchday?matchweek={1-38}` | Returns full matchday fixtures, predictions, quick facts & tactical insights |
| `POST` | `/api/match/insights` | Generates on-demand predictions & tactical analysis for custom matchups |

---

## 🧪 Testing

Run backend tests using `pytest`:

```bash
pytest
```

---

## 📁 Project Structure

```
statstrike/
├── configs/                             # Model & training configurations
│   ├── test_xg_efficient.yaml
│   └── default.yaml
├── data/
│   └── raw/premier/                     # Historical EPL, EFL & Fixture CSVs
├── frontend/                            # React + TypeScript + Vite UI
│   ├── public/
│   │   └── favicon.svg                  # Brand vector mark
│   ├── src/
│   │   ├── components/
│   │   │   ├── MatchCard.tsx            # Matchday prediction card
│   │   │   ├── MatchDetailModal.tsx     # "Why" explanation & quick facts
│   │   │   ├── MatchdayHeader.tsx       # Gameweek picker & navigation
│   │   │   ├── CustomSimulator.tsx      # Custom fixture simulator
│   │   │   └── StatStrikeLogo.tsx       # Vector brand logo component
│   │   ├── types/matchday.ts            # TypeScript interfaces
│   │   ├── App.tsx
│   │   └── index.css                    # Glassmorphism design system
├── models/                              # Trained ML model weights (.pkl)
├── src/premier_league_predictor/        # Python backend package
│   ├── server.py                        # FastAPI endpoints & CORS
│   ├── matchday.py                      # Matchday predictions & narrative engine
│   ├── data.py                          # Data loading & team name normalizer
│   ├── data_updater.py                  # In-season weekly data synchronization
│   ├── model.py                         # Dixon-Coles & ML model definitions
│   └── prediction.py                    # Prediction inference pipeline
└── tests/                               # Test suite
```

---

## 📄 License
MIT License.
