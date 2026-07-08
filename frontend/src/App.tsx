import React, { useState, useRef } from 'react';
import axios from 'axios';
import { UploadCloud, CheckCircle, Activity, ChevronRight } from 'lucide-react';
import './index.css';

const TEAMS = [
  "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
  "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich",
  "Leicester", "Liverpool", "Man City", "Man Utd", "Newcastle",
  "Nott'm Forest", "Southampton", "Tottenham", "West Ham", "Wolves"
].sort();

function App() {
  const [homeTeam, setHomeTeam] = useState(TEAMS[0]);
  const [awayTeam, setAwayTeam] = useState(TEAMS[1]);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState<any>(null);
  
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setPrediction(null);
    try {
      // Date formatting for backend (DD/MM/YYYY)
      const [year, month, day] = date.split('-');
      const formattedDate = `${day}/${month}/${year}`;
      
      const res = await axios.post('/api/predict', {
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
      await axios.post('/api/upload', formData, {
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
      <h1>Premier League Oracle</h1>
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
              <select value={homeTeam} onChange={e => setHomeTeam(e.target.value)}>
                {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            
            <div className="form-group">
              <label>Away Team</label>
              <select value={awayTeam} onChange={e => setAwayTeam(e.target.value)}>
                {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            
            <div className="form-group">
              <label>Match Date</label>
              <input 
                type="date" 
                value={date} 
                onChange={e => setDate(e.target.value)}
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
          {prediction ? (
            <div className="result-card">
              <div className="match-title">
                {prediction.home_team} vs {prediction.away_team}
              </div>
              <div className="match-date">{prediction.date}</div>
              
              <div className="prediction-badge">
                Prediction: {prediction.prediction === '1' || prediction.prediction === 'H' ? 'HOME WIN' : 'DRAW / AWAY WIN'}
              </div>
              
              {prediction.prob_home !== undefined && (
                <div style={{textAlign: 'left'}}>
                  <label>Win Probability</label>
                  <div className="probability-bar-container">
                    <div 
                      className="probability-fill" 
                      style={{width: `${prediction.prob_home * 100}%`}}
                    />
                  </div>
                  <div className="prob-labels">
                    <span>Home Win: {(prediction.prob_home * 100).toFixed(1)}%</span>
                    <span>Not Home Win: {((1 - prediction.prob_home) * 100).toFixed(1)}%</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{textAlign: 'center', color: 'var(--panel-border)'}}>
              <Activity size={48} style={{opacity: 0.5, marginBottom: '1rem'}} />
              <p>Awaiting match details...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
