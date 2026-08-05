import React from 'react';
import { Calendar, Trophy, Moon, Sun, Layers, Sparkles } from 'lucide-react';
import type { MatchdaySummary } from '../types/matchday';

interface MatchdayHeaderProps {
  round: string;
  season: string;
  totalFixtures: number;
  summary?: MatchdaySummary;
  activeFilter: 'all' | 'high_conf' | 'toss_up';
  onSelectFilter: (filter: 'all' | 'high_conf' | 'toss_up') => void;
  activeView: 'matchday' | 'custom';
  onSelectView: (view: 'matchday' | 'custom') => void;
  isLightMode: boolean;
  onToggleTheme: () => void;
}

export const MatchdayHeader: React.FC<MatchdayHeaderProps> = ({
  round,
  season,
  totalFixtures,
  summary,
  activeFilter,
  onSelectFilter,
  activeView,
  onSelectView,
  isLightMode,
  onToggleTheme,
}) => {
  return (
    <header className="matchday-header-container">
      <div className="header-top-row">
        <div className="brand-group">
          <div className="brand-badge">
            <Trophy className="brand-icon" size={24} />
            <div className="brand-info">
              <h1 className="brand-title">StatStrike</h1>
              <span className="brand-subtitle">Premier League ML Intelligence</span>
            </div>
          </div>
        </div>

        <div className="header-controls">
          <div className="view-switcher">
            <button
              className={`view-tab-btn ${activeView === 'matchday' ? 'active' : ''}`}
              onClick={() => onSelectView('matchday')}
            >
              <Calendar size={16} />
              <span>Matchday Hub</span>
            </button>
            <button
              className={`view-tab-btn ${activeView === 'custom' ? 'active' : ''}`}
              onClick={() => onSelectView('custom')}
            >
              <Layers size={16} />
              <span>Custom Simulator</span>
            </button>
          </div>

          <button
            className="theme-toggle-btn"
            onClick={onToggleTheme}
            title={isLightMode ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
            aria-label="Toggle Theme"
          >
            {isLightMode ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>
      </div>

      {activeView === 'matchday' && (
        <div className="matchday-banner glass-panel">
          <div className="matchday-meta">
            <div className="matchday-title-row">
              <span className="live-pulse-dot"></span>
              <h2 className="matchday-round-title">{round}</h2>
              <span className="season-pill">{season}</span>
            </div>
            <p className="matchday-desc">
              Algorithmic match outcomes, Poisson score distributions, and statistical driver breakdowns for all {totalFixtures} Premier League fixtures.
            </p>
          </div>

          {summary && (
            <div className="summary-stats-grid">
              <div className="summary-stat-pill">
                <span className="stat-num">{totalFixtures}</span>
                <span className="stat-label">Fixtures</span>
              </div>
              <div className="summary-stat-pill stat-home">
                <span className="stat-num">{summary.predicted_home_wins}</span>
                <span className="stat-label">Home Wins</span>
              </div>
              <div className="summary-stat-pill stat-draw">
                <span className="stat-num">{summary.predicted_draws}</span>
                <span className="stat-label">Draws</span>
              </div>
              <div className="summary-stat-pill stat-away">
                <span className="stat-num">{summary.predicted_away_wins}</span>
                <span className="stat-label">Away Wins</span>
              </div>
            </div>
          )}
        </div>
      )}

      {activeView === 'matchday' && (
        <div className="filter-toolbar">
          <div className="filter-tabs">
            <button
              className={`filter-btn ${activeFilter === 'all' ? 'active' : ''}`}
              onClick={() => onSelectFilter('all')}
            >
              All Matches ({totalFixtures})
            </button>
            <button
              className={`filter-btn ${activeFilter === 'high_conf' ? 'active' : ''}`}
              onClick={() => onSelectFilter('high_conf')}
            >
              <Sparkles size={14} />
              High Confidence
            </button>
            <button
              className={`filter-btn ${activeFilter === 'toss_up' ? 'active' : ''}`}
              onClick={() => onSelectFilter('toss_up')}
            >
              Upset Alerts / Toss-ups
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
