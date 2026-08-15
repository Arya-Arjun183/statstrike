import React, { useState } from 'react';
import { X, Sparkles, TrendingUp, Shield, Zap, MapPin, Swords, BarChart3, Clock, HelpCircle, Percent } from 'lucide-react';
import type { MatchFixture } from '../types/matchday';
import { getTeamLogo } from '../utils/teamAssets';
import { formatMatchDateTime } from '../utils/dateUtils';

interface MatchDetailModalProps {
  match: MatchFixture | null;
  onClose: () => void;
}

export const MatchDetailModal: React.FC<MatchDetailModalProps> = ({ match, onClose }) => {
  const [activeTab, setActiveTab] = useState<'why' | 'facts'>('why');

  if (!match) return null;

  const homePct = Math.round(match.prob_home * 100);
  const drawPct = Math.round(match.prob_draw * 100);
  const awayPct = Math.round(match.prob_away * 100);

  const localTimeInfo = formatMatchDateTime(match.date, match.time);

  const getPredictionTitle = () => {
    if (match.prediction === 'H') return `${match.home_team} Win`;
    if (match.prediction === 'A') return `${match.away_team} Win`;
    return 'Predicted Draw';
  };

  const getPredictionClass = () => {
    if (match.prediction === 'H') return 'pred-home';
    if (match.prediction === 'A') return 'pred-away';
    return 'pred-draw';
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-container glass-panel animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-matchup-hero">
            <div className="hero-team home">
              <img
                src={getTeamLogo(match.home_team)}
                alt={match.home_team}
                className="hero-team-logo"
              />
              <div className="hero-team-info">
                <span className="hero-team-name">{match.home_team}</span>
                <span className="hero-team-role">Home Side</span>
              </div>
            </div>

            <div className="hero-center-status">
              <div className="hero-meta-row">
                <Clock size={13} />
                <span>{localTimeInfo.fullLocalDisplay}</span>
              </div>
              <div className={`pred-outcome-pill large ${getPredictionClass()}`}>
                {getPredictionTitle()}
              </div>
              <div className="hero-venue-row">
                <MapPin size={12} />
                <span>{match.venue}</span>
              </div>
            </div>

            <div className="hero-team away">
              <img
                src={getTeamLogo(match.away_team)}
                alt={match.away_team}
                className="hero-team-logo"
              />
              <div className="hero-team-info">
                <span className="hero-team-name">{match.away_team}</span>
                <span className="hero-team-role">Away Side</span>
              </div>
            </div>
          </div>

          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        {/* Win Probability Bar in Modal */}
        <div className="modal-prob-section">
          <div className="modal-prob-labels">
            <span className="prob-pill home-pill">
              <strong>{match.home_team}</strong> {homePct}%
            </span>
            <span className="prob-pill draw-pill">
              <strong>Draw</strong> {drawPct}%
            </span>
            <span className="prob-pill away-pill">
              <strong>{match.away_team}</strong> {awayPct}%
            </span>
          </div>
          <div className="prob-bar-track large">
            <div className="prob-segment seg-home" style={{ width: `${homePct}%` }} />
            <div className="prob-segment seg-draw" style={{ width: `${drawPct}%` }} />
            <div className="prob-segment seg-away" style={{ width: `${awayPct}%` }} />
          </div>
        </div>

        {/* Tabs Navigation */}
        <div className="modal-tabs-nav">
          <button
            className={`modal-tab-btn ${activeTab === 'why' ? 'active' : ''}`}
            onClick={() => setActiveTab('why')}
          >
            <Sparkles size={16} />
            <span>Why Our Model Predicted This</span>
          </button>
          <button
            className={`modal-tab-btn ${activeTab === 'facts' ? 'active' : ''}`}
            onClick={() => setActiveTab('facts')}
          >
            <BarChart3 size={16} />
            <span>Match Quick Facts</span>
          </button>
        </div>

        {/* Modal Body Content */}
        <div className="modal-body-scroll">
          {activeTab === 'why' ? (
            <div className="tab-content why-tab">
              {/* Dynamic Narrative Banner */}
              <div className="narrative-card">
                <div className="narrative-header">
                  <Sparkles size={18} className="sparkle-icon" />
                  <h4>Model Decision Rationale</h4>
                </div>
                <p className="narrative-text">{match.explanation.narrative}</p>
              </div>

              {/* Expected Goals & Top Scorelines Grid */}
              <div className="grid-two-col">
                {/* Expected Goals Breakdown */}
                <div className="sub-panel">
                  <div className="sub-panel-title">
                    <Zap size={16} />
                    <span className="tooltip-container">
                      Projected Expected Goals (xG)
                      <HelpCircle size={14} className="tooltip-icon" />
                      <span className="tooltip-text">xG: The number of goals a team is expected to score based on the quality of their chances.</span>
                    </span>
                  </div>
                  <div className="xg-compare-container">
                    <div className="xg-team-box home">
                      <span className="xg-val">{match.explanation.lambda_home}</span>
                      <span className="xg-team-label">{match.home_team}</span>
                      <span className="xg-role-sub">Projected xG</span>
                    </div>
                    <div className="xg-vs-divider">VS</div>
                    <div className="xg-team-box away">
                      <span className="xg-val">{match.explanation.lambda_away}</span>
                      <span className="xg-team-label">{match.away_team}</span>
                      <span className="xg-role-sub">Projected xG</span>
                    </div>
                  </div>
                  <div className="xg-metric-note">
                    * Derived from Dixon-Coles Poisson offense/defense intensity parameters with home pitch calibration.
                  </div>
                </div>

                {/* Most Probable Exact Scorelines */}
                <div className="sub-panel">
                  <div className="sub-panel-title">
                    <TrendingUp size={16} />
                    <span>Top Predicted Scorelines</span>
                  </div>
                  <div className="top-scores-list">
                    {match.explanation.top_scores.map((scoreItem, idx) => (
                      <div key={idx} className="score-row">
                        <span className="score-tag">{scoreItem.score}</span>
                        <div className="score-bar-wrap">
                          <div
                            className="score-bar-fill"
                            style={{ width: `${Math.min(100, scoreItem.pct * 5)}%` }}
                          />
                        </div>
                        <span className="score-pct">{scoreItem.pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Tactical Matchup Strength Bars */}
              <div className="sub-panel">
                <div className="sub-panel-title">
                  <Shield size={16} />
                  <span>Tactical Matchup Balance (0-100 Rating)</span>
                </div>
                <div className="tactical-bars-grid">
                  <div className="tactical-item">
                    <div className="tactical-label-row">
                      <span>{match.home_team} Attack</span>
                      <span className="rating-num">{match.explanation.tactical_ratings.home_attack}</span>
                    </div>
                    <div className="tactical-progress-track">
                      <div
                        className="tactical-progress-fill fill-blue"
                        style={{ width: `${match.explanation.tactical_ratings.home_attack}%` }}
                      />
                    </div>
                  </div>

                  <div className="tactical-item">
                    <div className="tactical-label-row">
                      <span>{match.away_team} Defense</span>
                      <span className="rating-num">{match.explanation.tactical_ratings.away_defense}</span>
                    </div>
                    <div className="tactical-progress-track">
                      <div
                        className="tactical-progress-fill fill-purple"
                        style={{ width: `${match.explanation.tactical_ratings.away_defense}%` }}
                      />
                    </div>
                  </div>

                  <div className="tactical-item">
                    <div className="tactical-label-row">
                      <span>{match.away_team} Attack</span>
                      <span className="rating-num">{match.explanation.tactical_ratings.away_attack}</span>
                    </div>
                    <div className="tactical-progress-track">
                      <div
                        className="tactical-progress-fill fill-blue"
                        style={{ width: `${match.explanation.tactical_ratings.away_attack}%` }}
                      />
                    </div>
                  </div>

                  <div className="tactical-item">
                    <div className="tactical-label-row">
                      <span>{match.home_team} Defense</span>
                      <span className="rating-num">{match.explanation.tactical_ratings.home_defense}</span>
                    </div>
                    <div className="tactical-progress-track">
                      <div
                        className="tactical-progress-fill fill-purple"
                        style={{ width: `${match.explanation.tactical_ratings.home_defense}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="tab-content facts-tab">
              {/* Betting Odds */}
              {/* Betting Odds */}
              {match.odds ? (
                <div className="sub-panel">
                  <div className="sub-panel-title">
                    <Percent size={16} />
                    <span>Betting Value Edge (+EV)</span>
                  </div>
                  <div className="elo-metric-card" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', textAlign: 'center' }}>
                    <div className="split-box" style={{ background: 'transparent' }}>
                      <span className="split-title">{match.home_team} Win</span>
                      <span className="split-stat">Model: {Math.round(match.prob_home * 100)}%</span>
                      <span className="split-sub" style={{ marginTop: '4px' }}>Bookie: {Math.round(match.odds.home_implied * 100)}% ({match.odds.home_odds})</span>
                      {match.prob_home > match.odds.home_implied + 0.03 && <span style={{color: '#10b981', fontWeight: 'bold', fontSize: '0.8rem', marginTop: '4px', display: 'inline-block'}}>+EV Edge</span>}
                    </div>
                    <div className="split-box" style={{ background: 'transparent' }}>
                      <span className="split-title">Draw</span>
                      <span className="split-stat">Model: {Math.round(match.prob_draw * 100)}%</span>
                      <span className="split-sub" style={{ marginTop: '4px' }}>Bookie: {Math.round(match.odds.draw_implied * 100)}% ({match.odds.draw_odds})</span>
                      {match.prob_draw > match.odds.draw_implied + 0.03 && <span style={{color: '#10b981', fontWeight: 'bold', fontSize: '0.8rem', marginTop: '4px', display: 'inline-block'}}>+EV Edge</span>}
                    </div>
                    <div className="split-box" style={{ background: 'transparent' }}>
                      <span className="split-title">{match.away_team} Win</span>
                      <span className="split-stat">Model: {Math.round(match.prob_away * 100)}%</span>
                      <span className="split-sub" style={{ marginTop: '4px' }}>Bookie: {Math.round(match.odds.away_implied * 100)}% ({match.odds.away_odds})</span>
                      {match.prob_away > match.odds.away_implied + 0.03 && <span style={{color: '#10b981', fontWeight: 'bold', fontSize: '0.8rem', marginTop: '4px', display: 'inline-block'}}>+EV Edge</span>}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="sub-panel">
                  <div className="sub-panel-title">
                    <Percent size={16} />
                    <span>Betting Value Edge (+EV)</span>
                  </div>
                  <div style={{ padding: '1.5rem', textAlign: 'center', backgroundColor: 'var(--bg-tertiary)', borderRadius: '0.5rem', border: '1px dashed var(--border-light)', color: 'var(--text-secondary)' }}>
                    <p style={{ margin: 0, fontSize: '0.9rem' }}>Live betting odds will become available closer to the match date.</p>
                  </div>
                </div>
              )}

              {/* Form Comparison */}
              <div className="sub-panel">
                <div className="sub-panel-title">
                  <TrendingUp size={16} />
                  <span>Overall Form (Last 5 Premier League Matches)</span>
                </div>
                <div className="form-comparison-grid">
                  {/* Home Team Form */}
                  <div className="form-team-column">
                    <div className="form-team-header">
                      <img src={getTeamLogo(match.home_team)} alt="" className="form-mini-logo" />
                      <strong>{match.home_team}</strong>
                    </div>
                    <div className="form-matches-list">
                      {match.quick_facts.home_form.length > 0 ? (
                        match.quick_facts.home_form.map((m, idx) => (
                          <div key={idx} className="form-match-item">
                            <span className={`form-badge badge-${m.result.toLowerCase()}`}>{m.result}</span>
                            <div className="form-match-details">
                              <span className="match-opp">{m.is_home ? 'vs' : '@'} {m.opponent}</span>
                              <span className="match-score">{m.score}</span>
                            </div>
                            <span className="match-xg-pill">{m.xg_for} xG</span>
                          </div>
                        ))
                      ) : (
                        <p className="no-data-hint">No prior season matches found</p>
                      )}
                    </div>
                  </div>

                  {/* Away Team Form */}
                  <div className="form-team-column">
                    <div className="form-team-header">
                      <img src={getTeamLogo(match.away_team)} alt="" className="form-mini-logo" />
                      <strong>{match.away_team}</strong>
                    </div>
                    <div className="form-matches-list">
                      {match.quick_facts.away_form.length > 0 ? (
                        match.quick_facts.away_form.map((m, idx) => (
                          <div key={idx} className="form-match-item">
                            <span className={`form-badge badge-${m.result.toLowerCase()}`}>{m.result}</span>
                            <div className="form-match-details">
                              <span className="match-opp">{m.is_home ? 'vs' : '@'} {m.opponent}</span>
                              <span className="match-score">{m.score}</span>
                            </div>
                            <span className="match-xg-pill">{m.xg_for} xG</span>
                          </div>
                        ))
                      ) : (
                        <p className="no-data-hint">No prior season matches found</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Head-to-Head Section */}
              <div className="grid-two-col">
                <div className="sub-panel">
                  <div className="sub-panel-title">
                    <Swords size={16} />
                    <span>Head-to-Head Record</span>
                  </div>
                  <div className="h2h-summary-row">
                    <div className="h2h-stat-box home">
                      <span className="h2h-stat-num">{match.quick_facts.h2h.home_wins}</span>
                      <span className="h2h-stat-lbl">{match.home_team} Wins</span>
                    </div>
                    <div className="h2h-stat-box draw">
                      <span className="h2h-stat-num">{match.quick_facts.h2h.draws}</span>
                      <span className="h2h-stat-lbl">Draws</span>
                    </div>
                    <div className="h2h-stat-box away">
                      <span className="h2h-stat-num">{match.quick_facts.h2h.away_wins}</span>
                      <span className="h2h-stat-lbl">{match.away_team} Wins</span>
                    </div>
                  </div>

                  <div className="recent-h2h-list">
                    {[...match.quick_facts.h2h.recent_matches].reverse().map((h, i) => (
                      <div key={i} className="h2h-match-row">
                        <span className="h2h-date">{h.date}</span>
                        <span className="h2h-score">{h.home_team} {h.score} {h.away_team}</span>
                        <span className="h2h-winner">{h.winner}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Elo & Venue Splits */}
                <div className="sub-panel">
                  <div className="sub-panel-title">
                    <Shield size={16} />
                    <span className="tooltip-container">
                      Elo Ratings & Venue Splits
                      <HelpCircle size={14} className="tooltip-icon" />
                      <span className="tooltip-text">Elo Rating: A measure of team strength based on past results. Higher is better.</span>
                    </span>
                  </div>
                  <div className="elo-metric-card">
                    <div className="elo-row">
                      <span className="elo-team">{match.home_team} Elo:</span>
                      <strong className="elo-score">{match.quick_facts.elo.home_elo}</strong>
                    </div>
                    <div className="elo-row">
                      <span className="elo-team">{match.away_team} Elo:</span>
                      <strong className="elo-score">{match.quick_facts.elo.away_elo}</strong>
                    </div>
                    <div className="elo-diff-pill">
                      Rating Delta: <strong>{match.quick_facts.elo.diff > 0 ? `+${match.quick_facts.elo.diff}` : match.quick_facts.elo.diff} pts</strong>
                    </div>
                  </div>

                  <div className="venue-splits-grid">
                    <div className="split-box">
                      <span className="split-title">{match.home_team} at Home</span>
                      <span className="split-stat">{match.quick_facts.home_split.win_pct}% Win Rate</span>
                      <span className="split-sub">Avg Scored: {match.quick_facts.home_split.avg_gf}</span>
                    </div>
                    <div className="split-box">
                      <span className="split-title">{match.away_team} Away</span>
                      <span className="split-stat">{match.quick_facts.away_split.win_pct}% Win Rate</span>
                      <span className="split-sub">Avg Scored: {match.quick_facts.away_split.avg_gf}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
