import requests
from understatapi import UnderstatClient

def verify_football_data():
    print("Checking Football-Data.co.uk...")
    url = "https://www.football-data.co.uk/mmz4252/2526/E0.csv"
    try:
        resp = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code in [200, 404]: # 404 is fine, means season hasn't started or file doesn't exist yet, but server is up
            print("✅ Football-Data.co.uk is reachable.")
        else:
            print(f"❌ Football-Data.co.uk returned unexpected status code: {resp.status_code}")
    except Exception as e:
        print(f"❌ Failed to reach Football-Data.co.uk: {e}")

def verify_understat():
    print("\nChecking Understat...")
    try:
        understat = UnderstatClient()
        # Just fetching the main league data to see if API responds
        data = understat.league(league="EPL").get_match_data(season="2024") # Use 2024 since it definitely exists
        if data is not None:
            print("✅ Understat API is reachable.")
        else:
            print("❌ Understat API returned no data.")
    except Exception as e:
         print(f"❌ Failed to reach Understat API: {e}")

if __name__ == "__main__":
    print("--- Data Source Health Check ---\n")
    verify_football_data()
    verify_understat()
    print("\n--------------------------------")
