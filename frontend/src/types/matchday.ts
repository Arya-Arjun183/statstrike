export interface FormMatch {
  result: 'W' | 'D' | 'L';
  opponent: string;
  score: string;
  is_home: boolean;
  date: string;
  xg_for: number;
  xg_against: number;
}

export interface H2HMatch {
  date: string;
  home_team: string;
  away_team: string;
  score: string;
  winner: string;
}

export interface SeasonSplit {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  win_pct: number;
  avg_gf: number;
  avg_ga: number;
  avg_xg: number;
}

export interface QuickFacts {
  home_form: FormMatch[];
  away_form: FormMatch[];
  home_form_summary: string;
  away_form_summary: string;
  h2h: {
    total_matches: number;
    home_wins: number;
    draws: number;
    away_wins: number;
    recent_matches: H2HMatch[];
  };
  home_split: SeasonSplit;
  away_split: SeasonSplit;
  elo: {
    home_elo: number;
    away_elo: number;
    diff: number;
  };
  rest_days: {
    home: number;
    away: number;
  };
}

export interface ScorelineProbability {
  score: string;
  home_goals: number;
  away_goals: number;
  prob: number;
  pct: number;
}

export interface TacticalRatings {
  home_attack: number;
  home_defense: number;
  away_attack: number;
  away_defense: number;
}

export interface KeyFactor {
  factor: string;
  home_val: string;
  away_val: string;
}

export interface ModelExplanation {
  lambda_home: number;
  lambda_away: number;
  most_likely_score: string;
  top_scores: ScorelineProbability[];
  tactical_ratings: TacticalRatings;
  key_factors: KeyFactor[];
  narrative: string;
}

export interface MatchOdds {
  home_odds: number;
  draw_odds: number;
  away_odds: number;
  home_implied: number;
  draw_implied: number;
  away_implied: number;
}


export interface MatchFixture {
  fixture_id: number;
  home_team: string;
  away_team: string;
  date: string;
  time: string;
  venue: string;
  broadcaster?: string | null;
  prediction: 'H' | 'D' | 'A';
  prob_home: number;
  prob_draw: number;
  prob_away: number;
  confidence_label: string;
  confidence_class: 'confidence-high' | 'confidence-med' | 'confidence-low';
  most_likely_score: string;
  quick_facts: QuickFacts;
  explanation: ModelExplanation;
  odds?: MatchOdds | null;
}

export interface MatchdaySummary {
  predicted_home_wins: number;
  predicted_draws: number;
  predicted_away_wins: number;
}

export interface MatchdayOverview {
  round: string;
  season: string;
  current_matchweek?: number;
  available_matchweeks?: number[];
  total_fixtures: number;
  summary: MatchdaySummary;
  matches: MatchFixture[];
}
