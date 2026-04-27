import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION - VALIDE TES ABREVIATIONS ICI
# ==========================================
# Note: Si tu vois des codes différents dans tes logs GitHub, 
# remplace-les ici (ex: 'MON' au lieu de 'MTL').
TEAMS = {
    "NHL": ["MTL", "COL"], 
    "NBA": ["TOR"]
}

def fetch_nhl():
    print("--- Scraping NHL Data ---")
    games = []
    url = "https://api-web.nhle.com/v1/score/now"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        for game in data.get('games', []):
            # On récupère les abréviations de l'API
            home = game['homeTeam']['abbreviation'].upper()
            away = game['awayTeam']['abbreviation'].upper()
            
            print(f"NHL - Match trouvé : {away} @ {home}")

            # On vérifie si l'une des deux équipes est dans notre liste
            if home in [t.upper() for t in TEAMS["NHL"]] or away in [t.upper() for t in TEAMS["NHL"]]:
                print(f"✅ MATCH D'INTÉRÊT (NHL) : {away} @ {home}")
                start_utc = datetime.fromisoformat(game['startTimeUTC'].replace('Z', '+00:00'))
                status = game.get('seriesSummary', {}).get('seriesStatusShort', "Séries Éliminatoires")
                
                games.append({
                    "league": "NHL 🏒",
                    "title": f"{away} @ {home}",
                    "desc": f"{status} - Match NHL",
                    "start": start_utc
                })
    except Exception as e:
        print(f"Erreur NHL : {e}")
    return games

def fetch_nba():
    print("--- Scraping NBA Data ---")
    games = []
    url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        for game in data.get('scoreboard', {}).get('games', []):
            home = game['homeTeam']['teamAbbreviation'].upper()
            away = game['awayTeam']['teamAbbreviation'].upper()
            
            print(f"NBA - Match trouvé : {away} @ {home}")

            if home in [t.upper() for t in TEAMS["NBA"]] or away in [t.upper() for t in TEAMS["NBA"]]:
                print(f"✅ MATCH D'INTÉRÊT (NBA) : {away} @ {home}")
                # La NBA fournit souvent l'heure locale, on la convertit
                start_utc = datetime.fromisoformat(game['gameEt'].replace('Z', '+00:00'))
                games.append({
                    "league": "NBA 🏀",
                    "title": f"{away} @ {home}",
                    "desc": f"Match NBA - {game.get('gameStatusText', 'À venir')}",
                    "start": start_utc
                })
    except Exception as e:
        print(f"Erreur NBA : {e}")
    return games

def generate_xml(all_games):
    print(f"--- Génération XML : {len(all_games)} match(s) trouvé(s) ---")
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"

    if not all_games:
        # Bloc par défaut si rien n'est trouvé
        now = datetime.now(pytz.UTC)
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Pas de match pour MTL/COL/TOR"
        ET.SubElement(prog, "desc").text = "Vérifie tes abréviations si un match devrait être là."
    else:
        for game in sorted(all_games, key=lambda x: x['start']):
            start_str = game['start'].strftime("%Y%m%d%H%M%S +0000")
            stop_str = (game['start'] + timedelta(hours=3, minutes=30)).strftime("%Y%m%d%H%M%S +0000")
            
            prog = ET.SubElement(root, "programme", start=start_str, stop=stop_str, channel="Sports.Perso")
            ET.SubElement(prog, "title").text = f"{game['league']} | {game['title']}"
            ET.SubElement(prog, "desc").text = game['desc']

    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl() + fetch_nba()
    generate_xml(data)
    
