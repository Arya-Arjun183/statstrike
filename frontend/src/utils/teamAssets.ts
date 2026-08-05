export const TEAM_LOGOS: Record<string, string> = {
  "Arsenal": "https://a.espncdn.com/i/teamlogos/soccer/500/359.png",
  "Aston Villa": "https://a.espncdn.com/i/teamlogos/soccer/500/362.png",
  "Bournemouth": "https://a.espncdn.com/i/teamlogos/soccer/500/349.png",
  "Brentford": "https://a.espncdn.com/i/teamlogos/soccer/500/337.png",
  "Brighton": "https://a.espncdn.com/i/teamlogos/soccer/500/331.png",
  "Brighton and Hove Albion": "https://a.espncdn.com/i/teamlogos/soccer/500/331.png",
  "Burnley": "https://a.espncdn.com/i/teamlogos/soccer/500/379.png",
  "Chelsea": "https://a.espncdn.com/i/teamlogos/soccer/500/363.png",
  "Crystal Palace": "https://a.espncdn.com/i/teamlogos/soccer/500/384.png",
  "Everton": "https://a.espncdn.com/i/teamlogos/soccer/500/368.png",
  "Fulham": "https://a.espncdn.com/i/teamlogos/soccer/500/370.png",
  "Ipswich": "https://upload.wikimedia.org/wikipedia/en/thumb/4/43/Ipswich_Town.svg/500px-Ipswich_Town.svg.png",
  "Ipswich Town": "https://upload.wikimedia.org/wikipedia/en/thumb/4/43/Ipswich_Town.svg/500px-Ipswich_Town.svg.png",
  "Leeds": "https://a.espncdn.com/i/teamlogos/soccer/500/357.png",
  "Leeds United": "https://a.espncdn.com/i/teamlogos/soccer/500/357.png",
  "Leicester": "https://a.espncdn.com/i/teamlogos/soccer/500/375.png",
  "Leicester City": "https://a.espncdn.com/i/teamlogos/soccer/500/375.png",
  "Liverpool": "https://a.espncdn.com/i/teamlogos/soccer/500/364.png",
  "Luton": "https://a.espncdn.com/i/teamlogos/soccer/500/390.png",
  "Luton Town": "https://a.espncdn.com/i/teamlogos/soccer/500/390.png",
  "Man City": "https://a.espncdn.com/i/teamlogos/soccer/500/382.png",
  "Manchester City": "https://a.espncdn.com/i/teamlogos/soccer/500/382.png",
  "Man Utd": "https://a.espncdn.com/i/teamlogos/soccer/500/360.png",
  "Man United": "https://a.espncdn.com/i/teamlogos/soccer/500/360.png",
  "Manchester United": "https://a.espncdn.com/i/teamlogos/soccer/500/360.png",
  "Newcastle": "https://a.espncdn.com/i/teamlogos/soccer/500/361.png",
  "Newcastle United": "https://a.espncdn.com/i/teamlogos/soccer/500/361.png",
  "Nott'm Forest": "https://a.espncdn.com/i/teamlogos/soccer/500/393.png",
  "Nottingham Forest": "https://a.espncdn.com/i/teamlogos/soccer/500/393.png",
  "Sheffield United": "https://a.espncdn.com/i/teamlogos/soccer/500/398.png",
  "Southampton": "https://a.espncdn.com/i/teamlogos/soccer/500/376.png",
  "Sunderland": "https://a.espncdn.com/i/teamlogos/soccer/500/366.png",
  "Tottenham": "https://a.espncdn.com/i/teamlogos/soccer/500/367.png",
  "Tottenham Hotspur": "https://a.espncdn.com/i/teamlogos/soccer/500/367.png",
  "West Ham": "https://a.espncdn.com/i/teamlogos/soccer/500/371.png",
  "West Ham United": "https://a.espncdn.com/i/teamlogos/soccer/500/371.png",
  "Wolves": "https://a.espncdn.com/i/teamlogos/soccer/500/380.png",
  "Wolverhampton Wanderers": "https://a.espncdn.com/i/teamlogos/soccer/500/380.png"
};

const DEFAULT_LOGO = "https://a.espncdn.com/i/teamlogos/soccer/500/default-team-logo.png";

export function getTeamLogo(teamName: string): string {
  if (!teamName) return DEFAULT_LOGO;
  return TEAM_LOGOS[teamName] || DEFAULT_LOGO;
}

export const ALL_TEAMS = [
  "Arsenal",
  "Aston Villa",
  "Bournemouth",
  "Brentford",
  "Brighton",
  "Burnley",
  "Chelsea",
  "Crystal Palace",
  "Everton",
  "Fulham",
  "Ipswich",
  "Leeds",
  "Leicester",
  "Liverpool",
  "Manchester City",
  "Manchester United",
  "Newcastle United",
  "Nottingham Forest",
  "Southampton",
  "Sunderland",
  "Tottenham",
  "West Ham",
  "Wolverhampton Wanderers"
].sort();
