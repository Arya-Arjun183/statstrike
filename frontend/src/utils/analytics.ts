/**
 * Google Analytics 4 (GA4) custom event tracking helper
 */

declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
    dataLayer?: any[];
  }
}

export function trackEvent(eventName: string, params?: Record<string, any>) {
  if (typeof window !== 'undefined' && typeof window.gtag === 'function') {
    window.gtag('event', eventName, params);
  }
}

export function trackMatchInspect(homeTeam: string, awayTeam: string, matchweek?: number) {
  trackEvent('inspect_match', {
    event_category: 'engagement',
    matchup: `${homeTeam} vs ${awayTeam}`,
    home_team: homeTeam,
    away_team: awayTeam,
    matchweek: matchweek,
  });
}

export function trackSimulation(homeTeam: string, awayTeam: string, predictedWinner: string) {
  trackEvent('run_simulation', {
    event_category: 'simulator',
    matchup: `${homeTeam} vs ${awayTeam}`,
    home_team: homeTeam,
    away_team: awayTeam,
    predicted_winner: predictedWinner,
  });
}

export function trackGameweekChange(gameweek: number) {
  trackEvent('change_gameweek', {
    event_category: 'navigation',
    gameweek,
  });
}

export function trackFilterChange(filter: string) {
  trackEvent('filter_matches', {
    event_category: 'filter',
    filter_type: filter,
  });
}

export function trackThemeToggle(theme: 'light' | 'dark') {
  trackEvent('toggle_theme', {
    event_category: 'preferences',
    theme,
  });
}
