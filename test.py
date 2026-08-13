import requests
print(requests.get("http://127.0.0.1:8000/api/matchday?matchweek=1").json()['matches'][0]['odds'])
