import React, { useState, useRef } from 'react';
import axios from 'axios';
import { UploadCloud, CheckCircle, Activity, ChevronRight } from 'lucide-react';
import './index.css';

const TEAM_LOGOS: Record<string, string> = {
  "Arsenal": "https://a.espncdn.com/i/teamlogos/soccer/500/359.png",
  "Aston Villa": "https://a.espncdn.com/i/teamlogos/soccer/500/362.png",
  "Bournemouth": "https://a.espncdn.com/i/teamlogos/soccer/500/349.png",
  "Brentford": "https://a.espncdn.com/i/teamlogos/soccer/500/337.png",
  "Brighton": "https://a.espncdn.com/i/teamlogos/soccer/500/331.png",
  "Chelsea": "https://a.espncdn.com/i/teamlogos/soccer/500/363.png",
  "Crystal Palace": "https://a.espncdn.com/i/teamlogos/soccer/500/384.png",
  "Everton": "https://a.espncdn.com/i/teamlogos/soccer/500/368.png",
  "Fulham": "https://a.espncdn.com/i/teamlogos/soccer/500/370.png",
  "Ipswich": "https://upload.wikimedia.org/wikipedia/en/thumb/4/43/Ipswich_Town.svg/500px-Ipswich_Town.svg.png",
  "Leicester": "https://a.espncdn.com/i/teamlogos/soccer/500/375.png",
  "Liverpool": "https://a.espncdn.com/i/teamlogos/soccer/500/364.png",
  "Man City": "https://a.espncdn.com/i/teamlogos/soccer/500/382.png",
  "Man Utd": "https://a.espncdn.com/i/teamlogos/soccer/500/360.png",
  "Newcastle": "https://a.espncdn.com/i/teamlogos/soccer/500/361.png",
  "Nott'm Forest": "https://a.espncdn.com/i/teamlogos/soccer/500/393.png",
  "Southampton": "https://a.espncdn.com/i/teamlogos/soccer/500/376.png",
  "Tottenham": "https://a.espncdn.com/i/teamlogos/soccer/500/367.png",
  "West Ham": "https://a.espncdn.com/i/teamlogos/soccer/500/371.png",
  "Wolves": "https://a.espncdn.com/i/teamlogos/soccer/500/380.png"
};

const TEAMS = Object.keys(TEAM_LOGOS).sort();

function getConfidenceLevel(prob: number) {
  const maxProb = Math.max(prob, 1 - prob);
  if (maxProb >= 0.7) return { label: 'High Confidence', class: 'confidence-high' };
  if (maxProb >= 0.55) return { label: 'Moderate Confidence', class: 'confidence-med' };
  return { label: 'Toss Up', class: 'confidence-low' };
}

function App() {
  const [homeTeam, setHomeTeam] = useState(TEAMS[0]);
  const [awayTeam, setAwayTeam] = useState(TEAMS[1]);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState<any>(null);
  
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Use the Render URL if deployed, otherwise fallback to local proxy
  const API_URL = import.meta.env.VITE_API_BASE_URL || '/api';

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setPrediction(null);
    try {
      // Date formatting for backend (DD/MM/YYYY)
      const [year, month, day] = date.split('-');
      const formattedDate = `${day}/${month}/${year}`;
      
      const res = await axios.post(`${API_URL}/predict`, {
        home_team: homeTeam,
        away_team: awayTeam,
        date: formattedDate
      });
      if (res.data.results && res.data.results.length > 0) {
        setPrediction(res.data.results[0]);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to get prediction. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    setUploadStatus('uploading');
    try {
      await axios.post(`${API_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadStatus('success');
      setTimeout(() => setUploadStatus('idle'), 3000);
    } catch (err) {
      console.error(err);
      setUploadStatus('error');
    }
  };

  return (
    <div>
      <h1>StatStrike</h1>
      <p className="subtitle">AI-powered match predictions & betting analytics</p>

      <div className="app-grid">
        <div className="glass-panel">
          <h2>Match Details</h2>
          
          <div 
            className={`file-upload-zone ${uploadStatus === 'success' ? 'success' : ''}`}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploadStatus === 'uploading' ? (
              <Activity className="loader" style={{margin: '0 auto'}} />
            ) : uploadStatus === 'success' ? (
              <CheckCircle size={32} style={{margin: '0 auto'}} />
            ) : (
              <UploadCloud size={32} style={{margin: '0 auto', color: 'var(--accent-color)'}} />
            )}
            <p>{uploadStatus === 'success' ? 'Database Updated!' : 'Upload Latest CSV Data'}</p>
            <input 
              type="file" 
              accept=".csv" 
              ref={fileInputRef} 
              style={{display: 'none'}} 
              onChange={handleFileUpload}
            />
          </div>

          <form onSubmit={handlePredict}>
            <div className="form-group">
              <label>Home Team</label>
              <select value={homeTeam} onChange={e => { setHomeTeam(e.target.value); setPrediction(null); }}>
                {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            
            <div className="form-group">
              <label>Away Team</label>
              <select value={awayTeam} onChange={e => { setAwayTeam(e.target.value); setPrediction(null); }}>
                {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            
            <div className="form-group">
              <label>Match Date</label>
              <input 
                type="date" 
                value={date} 
                onChange={e => { setDate(e.target.value); setPrediction(null); }}
                required
              />
            </div>
            
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? <Activity className="loader" /> : 'Generate Prediction'}
              {!loading && <ChevronRight size={20} />}
            </button>
          </form>
        </div>

        <div className="glass-panel" style={{display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
          <div className="result-card">
            <div className="matchup-container">
              <div className="team-name-col">
                <img src={TEAM_LOGOS[prediction ? prediction.home_team : homeTeam]} alt={prediction ? prediction.home_team : homeTeam} className="team-logo" />
                <div className="match-title">{prediction ? prediction.home_team : homeTeam}</div>
              </div>
              <div className="vs-text">VS</div>
              <div className="team-name-col">
                <img src={TEAM_LOGOS[prediction ? prediction.away_team : awayTeam]} alt={prediction ? prediction.away_team : awayTeam} className="team-logo" />
                <div className="match-title">{prediction ? prediction.away_team : awayTeam}</div>
              </div>
            </div>
            <div className="match-date">{prediction ? prediction.date : date}</div>
            
            <div className="prediction-badge" style={{ visibility: prediction ? 'visible' : 'hidden' }}>
              Prediction: {prediction ? (prediction.prediction === '1' || prediction.prediction === 'H' ? 'HOME WIN' : 'DRAW / AWAY WIN') : 'NONE'}
            </div>
            
            <div style={{textAlign: 'left'}}>
              <label>Win Probability</label>
              <div className="probability-bar-container">
                <div 
                  className={`probability-fill ${loading ? 'calculating' : ''}`} 
                  style={
                    !loading ? {
                      width: prediction ? `${prediction.prob_home * 100}%` : '0%',
                      background: !prediction ? 'transparent' : undefined
                    } : undefined
                  }
                />
              </div>
              <div className="prob-labels">
                <span>Home Win: {prediction ? (prediction.prob_home * 100).toFixed(1) + '%' : '--%'}</span>
                <span>Not Home Win: {prediction ? ((1 - prediction.prob_home) * 100).toFixed(1) + '%' : '--%'}</span>
              </div>

              {/* Confidence Badge */}
              <div className="confidence-badge-wrapper" style={{textAlign: 'center', minHeight: '32px'}}>
                {loading ? (
                  <div className="confidence-badge" style={{background: 'transparent', border: '1px solid var(--panel-border)', color: 'var(--text-primary)', boxShadow: 'none'}}>
                    Calculating...
                  </div>
                ) : prediction ? (
                  <div className={`confidence-badge ${getConfidenceLevel(prediction.prob_home).class}`}>
                    {getConfidenceLevel(prediction.prob_home).label}
                  </div>
                ) : (
                  <div className="confidence-badge" style={{background: 'transparent', border: '1px solid var(--panel-border)', color: 'var(--text-primary)', boxShadow: 'none'}}>
                    Awaiting Prediction
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
