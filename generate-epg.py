import requests
import json
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

def fetch_debug_structure():
    print("=== AUTOPSIE DU JSON NHL ===")
    url = "https://api-web.nhle.com/v1/score/now"
    
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        games = data.get('games', [])
        
        if games:
            # On imprime la structure du premier match pour comprendre le nouveau format
            print("--- STRUCTURE BRUTE DU MATCH #1 ---")
            print(json.dumps(games[0], indent=2))
            print("-----------------------------------")
            
            # Tentative de détection dynamique
            g = games[0]
            # On cherche partout où il pourrait y avoir une abréviation
            possible_away = g.get('awayTeam', {}).get('abbreviation') or g.get('awayTeam', {}).get('commonName', {}).get('default')
            possible_home = g.get('homeTeam', {}).get('abbreviation') or g.get('homeTeam', {}).get('commonName', {}).get('default')
            
            print(f"Test détection : {possible_away} @ {possible_home}")
        else:
            print("Aucun match trouvé dans 'games'. Voici les clés à la racine :")
            print(data.keys())

    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    fetch_debug_structure()
    
