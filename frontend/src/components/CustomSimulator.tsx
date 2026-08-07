import React, { useState } from 'react';
import axios from 'axios';
import { Activity, ChevronRight, Sparkles, ArrowRight } from 'lucide-react';
import { ALL_TEAMS, getTeamLogo } from '../utils/teamAssets';
import type { MatchFixture } from '../types/matchday';

interface CustomSimulatorProps {
  onInspectMatch: (match: MatchFixture) => void;
}

export const CustomSimulator: React.FC<CustomSimulatorProps> = ({ onInspectMatch }) => {
  const [homeTeam, setHomeTeam] = useState(ALL_TEAMS[0]);
  const [awayTeam, setAwayTeam] = useState(ALL_TEAMS[1]);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);
  const [simulatedMatch, setSimulatedMatch] = useState<MatchFixture | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_BASE_URL || '';

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    setSimulatedMatch(null);

    try {
      const [year, month, day] = date.split('-');
      const formattedDate = `${day}/${month}/${year}`;

      const res = await axios.post(`${API_URL}/api/match/insights`, {
        home_team: homeTeam,
        away_team: awayTeam,
        date: formattedDate,
      });

      const data = res.data;
      const prob_h = data.prob_home || 0.45;
      const prob_d = data.prob_draw || 0.28;
      const prob_a = data.prob_away || 0.27;
      const max_p = Math.max(prob_h, prob_a);

      let conf_label = 'Toss Up';
      let conf_class: 'confidence-high' | 'confidence-med' | 'confidence-low' = 'confidence-low';
      if (max_p >= 0.58) {
        conf_label = 'High Confidence';
        conf_class = 'confidence-high';
      } else if (max_p >= 0.48) {
        conf_label = 'Moderate Confidence';
        conf_class = 'confidence-med';
      }

      const matchFixture: MatchFixture = {
        fixture_id: 999,
        home_team: data.home_team,
        away_team: data.away_team,
        date: data.date,
        time: '15:00',
        venue: 'Selected Venue',
        prediction: data.prediction,
        prob_home: prob_h,
        prob_draw: prob_d,
        prob_away: prob_a,
        confidence_label: conf_label,
        confidence_class: conf_class,
        most_likely_score: data.explanation.most_likely_score,
        quick_facts: data.quick_facts,
        explanation: data.explanation,
      };

      setSimulatedMatch(matchFixture);
    } catch (err: any) {
      console.error('Simulation error:', err);
      setErrorMsg(err?.response?.data?.detail || 'Failed to simulate match. Please verify the server is running.');
    } finally {
      setLoading(false);
    }
  };

  const getPredictionTitle = (m: MatchFixture) => {
    if (m.prediction === 'H') return `${m.home_team} Win`;
    if (m.prediction === 'A') return `${m.away_team} Win`;
    return 'Draw';
  };

  const getPredictionClass = (m: MatchFixture) => {
    if (m.prediction === 'H') return 'pred-home';
    if (m.prediction === 'A') return 'pred-away';
    return 'pred-draw';
  };

  return (
    <div className="custom-simulator-view">
      <div className="app-grid">
        {/* Form Panel */}
        <div className="glass-panel">
          <h2 className="panel-heading">Configure Matchup</h2>
          <p className="panel-sub">Select any two Premier League clubs to run custom model inference.</p>

          <form onSubmit={handleSimulate} className="sim-form">
            <div className="form-group">
              <label>Home Team</label>
              <select
                value={homeTeam}
                onChange={(e) => {
                  setHomeTeam(e.target.value);
                  setSimulatedMatch(null);
                }}
              >
                {ALL_TEAMS.filter((t) => t !== awayTeam).map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Away Team</label>
              <select
                value={awayTeam}
                onChange={(e) => {
                  setAwayTeam(e.target.value);
                  setSimulatedMatch(null);
                }}
              >
                {ALL_TEAMS.filter((t) => t !== homeTeam).map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Match Date</label>
              <input
                type="date"
                value={date}
                onChange={(e) => {
                  setDate(e.target.value);
                  setSimulatedMatch(null);
                }}
                required
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? <Activity className="loader" size={18} /> : <Sparkles size={18} />}
              <span>{loading ? 'Calculating Probabilities...' : 'Simulate Match Outcome'}</span>
              {!loading && <ChevronRight size={18} />}
            </button>
          </form>

          {errorMsg && <div className="error-alert">{errorMsg}</div>}
        </div>

        {/* Output Panel */}
        <div className="glass-panel result-side-panel">
          <h2 className="panel-heading">Simulation Result</h2>
          {simulatedMatch ? (
            <div className="sim-result-box">
              <div className="sim-matchup-hero">
                <div className="sim-team-col">
                  <img src={getTeamLogo(simulatedMatch.home_team)} alt="" className="sim-team-logo" />
                  <span className="sim-team-name">{simulatedMatch.home_team}</span>
                </div>
                <span className="sim-vs">VS</span>
                <div className="sim-team-col">
                  <img src={getTeamLogo(simulatedMatch.away_team)} alt="" className="sim-team-logo" />
                  <span className="sim-team-name">{simulatedMatch.away_team}</span>
                </div>
              </div>

              <div className="sim-outcome-wrapper">
                <div className={`pred-outcome-pill ${getPredictionClass(simulatedMatch)}`}>
                  {getPredictionTitle(simulatedMatch)}
                </div>
                <div className={`confidence-tag ${simulatedMatch.confidence_class}`}>
                  {simulatedMatch.confidence_label}
                </div>
              </div>

              {/* Probabilities */}
              <div className="prob-bar-container" style={{ width: '100%', marginTop: '1.25rem' }}>
                <div className="prob-labels-row">
                  <span className="prob-label home-val">{Math.round(simulatedMatch.prob_home * 100)}%</span>
                  <span className="prob-label draw-val">{Math.round(simulatedMatch.prob_draw * 100)}% Draw</span>
                  <span className="prob-label away-val">{Math.round(simulatedMatch.prob_away * 100)}%</span>
                </div>
                <div className="prob-bar-track">
                  <div className="prob-segment seg-home" style={{ width: `${Math.round(simulatedMatch.prob_home * 100)}%` }} />
                  <div className="prob-segment seg-draw" style={{ width: `${Math.round(simulatedMatch.prob_draw * 100)}%` }} />
                  <div className="prob-segment seg-away" style={{ width: `${Math.round(simulatedMatch.prob_away * 100)}%` }} />
                </div>
              </div>

              <div className="sim-score-hint">
                Most Likely Score: <strong>{simulatedMatch.most_likely_score}</strong>
              </div>

              <button
                type="button"
                className="btn-inspect-breakdown"
                onClick={() => onInspectMatch(simulatedMatch)}
              >
                <span>View Deep Quick Facts & Explainability</span>
                <ArrowRight size={16} />
              </button>
            </div>
          ) : (
            <div className="empty-sim-placeholder">
              <Sparkles size={36} className="placeholder-icon" />
              <p>Configure two teams on the left and click Simulate to generate full model metrics and Poisson score distributions.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
