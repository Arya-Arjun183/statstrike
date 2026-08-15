import React from 'react';
import { Moon, Sun, Sparkles, MessageSquarePlus } from 'lucide-react';
import { StatStrikeLogo } from './StatStrikeLogo';
import type { MatchdaySummary } from '../types/matchday';

interface MatchdayHeaderProps {
  round: string;
  season: string;
  totalFixtures: number;
  currentMatchweek?: number;
  availableMatchweeks?: number[];
  onSelectMatchweek?: (mw: number) => void;
  summary?: MatchdaySummary;
  activeFilter: 'all' | 'high_conf' | 'toss_up';
  onSelectFilter: (filter: 'all' | 'high_conf' | 'toss_up') => void;
  isLightMode: boolean;
  onToggleTheme: () => void;
  onOpenFeedback: () => void;
}

export const MatchdayHeader: React.FC<MatchdayHeaderProps> = ({
  round,
  season,
  totalFixtures,
  currentMatchweek = 1,
  availableMatchweeks = [1],
  onSelectMatchweek,
  summary,
  activeFilter,
  onSelectFilter,
  isLightMode,
  onToggleTheme,
  onOpenFeedback,
}) => {
  return (
    <header className="matchday-header-container">
      <div className="header-top-row">
        <div className="brand-group">
          <div className="brand-badge">
            <StatStrikeLogo size={36} />
            <div className="brand-info">
              <h1 className="brand-title">StatStrike</h1>
              <span className="brand-subtitle">Premier League ML Intelligence</span>
            </div>
          </div>
        </div>

        <div className="header-controls">
          <div className="view-switcher">
            <button
              className="view-tab-btn"
              onClick={onOpenFeedback}
            >
              <MessageSquarePlus size={16} />
              <span>Feedback</span>
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

        <div className="matchday-banner glass-panel">
          <div className="matchday-meta">
            <div className="matchday-title-row">
              <span className="live-pulse-dot"></span>
              <h2 className="matchday-round-title">{round}</h2>
              <span className="season-pill">{season}</span>
              
              {availableMatchweeks && availableMatchweeks.length > 1 && onSelectMatchweek && (
                <div className="gameweek-select-wrapper">
                  <select
                    className="gameweek-dropdown"
                    value={currentMatchweek}
                    onChange={(e) => onSelectMatchweek(Number(e.target.value))}
                    aria-label="Select Gameweek"
                  >
                    {availableMatchweeks.map((mw) => (
                      <option key={mw} value={mw}>
                        Gameweek {mw}
                      </option>
                    ))}
                  </select>
                </div>
              )}
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
    </header>
  );
};
