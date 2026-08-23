import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Activity, AlertCircle, RefreshCw } from 'lucide-react';
import { MatchdayHeader } from './components/MatchdayHeader';
import { MatchCard } from './components/MatchCard';
import { MatchDetailModal } from './components/MatchDetailModal';
import FeedbackModal from './components/FeedbackModal';
import DataCreditModal from './components/DataCreditModal';
import type { MatchFixture, MatchdayOverview } from './types/matchday';
import {
  trackMatchInspect,
  trackGameweekChange,
  trackFilterChange,
  trackThemeToggle,
} from './utils/analytics';
import './index.css';

export function App() {
  const [matchdayData, setMatchdayData] = useState<MatchdayOverview | null>(null);
  const [selectedMatchweek, setSelectedMatchweek] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<MatchFixture | null>(null);
  const [activeFilter, setActiveFilter] = useState<'all' | 'high_conf' | 'toss_up'>('all');
  const [isLightMode, setIsLightMode] = useState<boolean>(false);
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [isCreditsOpen, setIsCreditsOpen] = useState(false);

  const API_URL = import.meta.env.VITE_API_BASE_URL || '';

  const fetchMatchday = useCallback(async (mw: number) => {
    setLoading(true);
    setError(null);
    try {
      const url = mw > 0 ? `${API_URL}/api/matchday?matchweek=${mw}` : `${API_URL}/api/matchday`;
      const res = await axios.get(url);
      setMatchdayData(res.data);
      if (res.data?.current_matchweek && mw === 0) {
        setSelectedMatchweek(res.data.current_matchweek);
      }
    } catch (err: any) {
      console.error('Failed to load matchday predictions:', err);
      setError(err?.response?.data?.detail || 'Unable to connect to the prediction server.');
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchMatchday(0);
  }, [fetchMatchday]);

  const handleSelectMatchweek = (mw: number) => {
    setSelectedMatchweek(mw);
    fetchMatchday(mw);
    trackGameweekChange(mw);
  };

  const handleSelectMatch = (m: MatchFixture) => {
    setSelectedMatch(m);
    trackMatchInspect(m.home_team, m.away_team, selectedMatchweek);
  };

  const handleFilterChange = (filter: 'all' | 'high_conf' | 'toss_up') => {
    setActiveFilter(filter);
    trackFilterChange(filter);
  };

  useEffect(() => {
    if (isLightMode) {
      document.body.classList.add('light-mode');
    } else {
      document.body.classList.remove('light-mode');
    }
  }, [isLightMode]);

  const toggleTheme = () => {
    setIsLightMode((prev) => {
      const next = !prev;
      trackThemeToggle(next ? 'light' : 'dark');
      return next;
    });
  };

  const getFilteredMatches = (): MatchFixture[] => {
    if (!matchdayData || !matchdayData.matches) return [];
    if (activeFilter === 'high_conf') {
      return matchdayData.matches.filter((m) => m.confidence_class === 'confidence-high');
    }
    if (activeFilter === 'toss_up') {
      return matchdayData.matches.filter(
        (m) => m.confidence_class === 'confidence-low' || m.prediction === 'D'
      );
    }
    return matchdayData.matches;
  };

  const filteredMatches = getFilteredMatches();

  return (
    <div className="app-shell">
      {/* Top Header & Overview Banner */}
      <MatchdayHeader
        round={matchdayData?.round || `Gameweek ${selectedMatchweek}`}
        season={matchdayData?.season || '2026/27'}
        totalFixtures={matchdayData?.total_fixtures || 10}
        currentMatchweek={matchdayData?.current_matchweek || selectedMatchweek}
        availableMatchweeks={matchdayData?.available_matchweeks || Array.from({ length: 38 }, (_, i) => i + 1)}
        onSelectMatchweek={handleSelectMatchweek}
        summary={matchdayData?.summary}
        activeFilter={activeFilter}
        onSelectFilter={handleFilterChange}
        isLightMode={isLightMode}
        onToggleTheme={toggleTheme}
        onOpenFeedback={() => setIsFeedbackOpen(true)}
        onOpenCredits={() => setIsCreditsOpen(true)}
      />

      {/* Main Content Area */}
      <main className="main-content">
      {loading && (
        <div className="state-card glass-panel">
          <Activity className="loader spinner-large" size={40} />
          <h3 className="loading-title">Calculating Matchday Predictions...</h3>
          <p className="loading-desc">
            Running Dixon-Coles Poisson simulations, extracting team forms, and computing exact scoreline likelihoods for all fixtures.
          </p>
        </div>
      )}

      {error && !loading && (
        <div className="state-card glass-panel error-card">
          <AlertCircle size={44} className="error-icon" />
          <h3 className="error-title">Failed to Load Matchday Data</h3>
          <p className="error-desc">{error}</p>
          <button className="btn-primary retry-btn" onClick={() => fetchMatchday(selectedMatchweek)}>
            <RefreshCw size={16} />
            <span>Retry Calculation</span>
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="matches-grid">
          {filteredMatches.length > 0 ? (
            filteredMatches.map((match) => (
              <MatchCard
                key={match.fixture_id}
                match={match}
                onSelectMatch={handleSelectMatch}
              />
            ))
          ) : (
            <div className="empty-filter-state glass-panel">
              <p>No matches match the selected filter.</p>
              <button className="btn-primary" onClick={() => handleFilterChange('all')}>
                Show All Matches
              </button>
            </div>
          )}
        </div>
      )}
      </main>

      {/* Interactive Match Detail Modal */}
      <MatchDetailModal
        match={selectedMatch}
        onClose={() => setSelectedMatch(null)}
      />

      {/* Feedback Modal */}
      <FeedbackModal
        isOpen={isFeedbackOpen}
        onClose={() => setIsFeedbackOpen(false)}
      />

      {/* Credits Modal */}
      <DataCreditModal
        isOpen={isCreditsOpen}
        onClose={() => setIsCreditsOpen(false)}
      />
    </div>
  );
}

export default App;
