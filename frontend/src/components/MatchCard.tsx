import React from 'react';
import { ArrowRight, Clock, MapPin, Sparkles } from 'lucide-react';
import type { MatchFixture } from '../types/matchday';
import { getTeamLogo } from '../utils/teamAssets';
import { formatMatchDateTime } from '../utils/dateUtils';

interface MatchCardProps {
  match: MatchFixture;
  onSelectMatch: (match: MatchFixture) => void;
}

export const MatchCard: React.FC<MatchCardProps> = ({ match, onSelectMatch }) => {
  const homePct = Math.round(match.prob_home * 100);
  const drawPct = Math.round(match.prob_draw * 100);
  const awayPct = Math.round(match.prob_away * 100);

  const localTimeInfo = formatMatchDateTime(match.date, match.time);

  const getValueBetText = () => {
    if (!match.odds) return null;
    if (match.prediction === 'H' && match.prob_home > match.odds.home_implied + 0.03) return '+EV Home';
    if (match.prediction === 'A' && match.prob_away > match.odds.away_implied + 0.03) return '+EV Away';
    if (match.prediction === 'D' && match.prob_draw > match.odds.draw_implied + 0.03) return '+EV Draw';
    return null;
  };

  const valueBet = getValueBetText();

  const getPredictionTitle = () => {
    if (match.prediction === 'H') return `${match.home_team} Win`;
    if (match.prediction === 'A') return `${match.away_team} Win`;
    return 'Draw';
  };

  const getPredictionClass = () => {
    if (match.prediction === 'H') return 'pred-home';
    if (match.prediction === 'A') return 'pred-away';
    return 'pred-draw';
  };

  return (
    <div
      className="match-card glass-panel"
      onClick={() => onSelectMatch(match)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelectMatch(match)}
    >
      <div className="card-top-meta">
        <div className="meta-time">
          <Clock size={13} />
          <span>{localTimeInfo.fullLocalDisplay}</span>
        </div>
        <div className={`confidence-tag ${match.confidence_class}`}>
          {match.confidence_class === 'confidence-high' && <Sparkles size={11} />}
          <span>{match.confidence_label}</span>
        </div>
      </div>

      <div className="card-matchup-row">
        {/* Home Team */}
        <div className="team-cell team-home">
          <img
            src={getTeamLogo(match.home_team)}
            alt={match.home_team}
            className="team-card-logo"
            loading="lazy"
          />
          <span className="team-card-name" title={match.home_team}>{match.home_team}</span>
          <div className="form-mini-row" title="Overall Form (Last 5 Matches)">
            {match.quick_facts.home_form.map((f, i) => (
              <span key={i} className={`form-mini-dot form-${f.result.toLowerCase()}`} title={`${f.result} vs ${f.opponent} (${f.score})`}>
                {f.result}
              </span>
            ))}
          </div>
        </div>

        {/* Center VS / Prediction */}
        <div className="center-vs-cell">
          <span className="vs-badge">VS</span>
          <div className={`pred-outcome-pill ${getPredictionClass()}`}>
            {getPredictionTitle()}
          </div>
          {valueBet && (
            <div className="ev-badge" style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 600, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '2px' }}>
              <Sparkles size={10} /> {valueBet}
            </div>
          )}
          <div className="score-hint">
            Top Score: <strong>{match.most_likely_score}</strong>
          </div>
        </div>

        {/* Away Team */}
        <div className="team-cell team-away">
          <img
            src={getTeamLogo(match.away_team)}
            alt={match.away_team}
            className="team-card-logo"
            loading="lazy"
          />
          <span className="team-card-name" title={match.away_team}>{match.away_team}</span>
          <div className="form-mini-row" title="Overall Form (Last 5 Matches)">
            {match.quick_facts.away_form.map((f, i) => (
              <span key={i} className={`form-mini-dot form-${f.result.toLowerCase()}`} title={`${f.result} vs ${f.opponent} (${f.score})`}>
                {f.result}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Tri-color Probability Bar */}
      <div className="prob-bar-container">
        <div className="prob-labels-row">
          <span className="prob-label home-val">{homePct}%</span>
          <span className="prob-label draw-val">{drawPct}% Draw</span>
          <span className="prob-label away-val">{awayPct}%</span>
        </div>
        <div className="prob-bar-track">
          <div
            className="prob-segment seg-home"
            style={{ width: `${homePct}%` }}
            title={`Home Win: ${homePct}%`}
          />
          <div
            className="prob-segment seg-draw"
            style={{ width: `${drawPct}%` }}
            title={`Draw: ${drawPct}%`}
          />
          <div
            className="prob-segment seg-away"
            style={{ width: `${awayPct}%` }}
            title={`Away Win: ${awayPct}%`}
          />
        </div>
      </div>

      {/* Footer Info & Action */}
      <div className="card-footer-row">
        <div className="footer-venue">
          <MapPin size={12} />
          <span>{match.venue}</span>
        </div>
        <div className="breakdown-link">
          <span>Quick Facts & Why</span>
          <ArrowRight size={14} className="arrow-icon" />
        </div>
      </div>
    </div>
  );
};
