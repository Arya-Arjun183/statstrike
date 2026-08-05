import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Activity, AlertCircle, RefreshCw } from 'lucide-react';
import { MatchdayHeader } from './components/MatchdayHeader';
import { MatchCard } from './components/MatchCard';
import { MatchDetailModal } from './components/MatchDetailModal';
import { CustomSimulator } from './components/CustomSimulator';
import type { MatchFixture, MatchdayOverview } from './types/matchday';
import './index.css';

export function App() {
  const [matchdayData, setMatchdayData] = useState<MatchdayOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<MatchFixture | null>(null);
  const [activeFilter, setActiveFilter] = useState<'all' | 'high_conf' | 'toss_up'>('all');
  const [activeView, setActiveView] = useState<'matchday' | 'custom'>('matchday');
  const [isLightMode, setIsLightMode] = useState<boolean>(false);

  const API_URL = import.meta.env.VITE_API_BASE_URL || '';

  const fetchMatchday = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_URL}/api/matchday`);
      setMatchdayData(res.data);
    } catch (err: any) {
      console.error('Failed to load matchday predictions:', err);
      setError(err?.response?.data?.detail || 'Unable to connect to the prediction server.');
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchMatchday();
  }, [fetchMatchday]);

  useEffect(() => {
    if (isLightMode) {
      document.body.classList.add('light-mode');
    } else {
      document.body.classList.remove('light-mode');
    }
  }, [isLightMode]);

  const toggleTheme = () => {
    setIsLightMode((prev) => !prev);
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
    <div className="statstrike-app">
      {/* Header */}
      <MatchdayHeader
        round={matchdayData?.round || 'Gameweek 1'}
        season={matchdayData?.season || '2026/27'}
        totalFixtures={matchdayData?.total_fixtures || 10}
        summary={matchdayData?.summary}
        activeFilter={activeFilter}
        onSelectFilter={setActiveFilter}
        activeView={activeView}
        onSelectView={setActiveView}
        isLightMode={isLightMode}
        onToggleTheme={toggleTheme}
      />

      {/* Main Content Area */}
      <main className="main-content">
        {activeView === 'matchday' ? (
          <>
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
                <button className="btn-primary retry-btn" onClick={fetchMatchday}>
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
                      onSelectMatch={(m) => setSelectedMatch(m)}
                    />
                  ))
                ) : (
                  <div className="empty-filter-state glass-panel">
                    <p>No matches match the selected filter.</p>
                    <button className="btn-primary" onClick={() => setActiveFilter('all')}>
                      Show All Matches
                    </button>
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <CustomSimulator onInspectMatch={(m) => setSelectedMatch(m)} />
        )}
      </main>

      {/* Interactive Match Detail Modal */}
      <MatchDetailModal
        match={selectedMatch}
        onClose={() => setSelectedMatch(null)}
      />
    </div>
  );
}

export default App;
