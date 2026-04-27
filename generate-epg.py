import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET
import sys

# ==========================================
# CONFIGURATION
# ==========================================
# Assure-toi que les abréviations correspondent aux APIs
TEAMS = {
    "NHL": ["MTL", "COL"], 
    "NBA": ["TOR"]
}

# Fuseau horaire pour l'affichage (Heure de l'Est)
LOCAL_TZ = pytz.timezone("America/Toronto")

def fetch_nhl():
    print("--- Scraping NHL Data ---")
    games = []
    # L'endpoint /score/now est le plus fiable pour les matchs du jour et les scores
    url = "https://api-web.nhle.com/v1/score/now"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        found_games = data.get('games', [])
        print(f"Nombre total de matchs NHL aujourd'hui : {len(found_games)}")

        for game in found_games:
            home = game['homeTeam']['abbreviation']
            away = game['awayTeam']['abbreviation']
            
            if home in TEAMS["NHL"] or away in TEAMS["NHL"]:
                print(f"Match d'intérêt trouvé : {away} @ {home}")
                # Format date : 2026-04-27T23:00:00Z
                start_utc = datetime.fromisoformat(game['startTimeUTC'].replace('Z', '+00:00'))
                
                status = game.get('seriesSummary', {}).get('seriesStatusShort', "Match de séries")
                
                games.append({
                    "league": "NHL 🏒",
                    "title": f"{away} @ {home}",
                    "desc": f"{status} - En direct de {game.get('venue', {}).get('default', 'l''aréna')}",
                    "start": start_utc
                })
    except Exception as e:
        print(f"Erreur NHL : {e}")
    return games

def fetch_nba():
    print("--- Scraping NBA Data ---")
    games = []
    # API CDN NBA (plus stable pour les scripts automatisés)
    url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        scoreboard = data.get('scoreboard', {})
        found_games = scoreboard.get('games', [])
        
        print(f"Nombre total de matchs NBA aujourd'hui : {len(found_games)}")

        for game in found_games:
            home = game['homeTeam']['teamAbbreviation']
            away = game['awayTeam']['teamAbbreviation']
            
            if home in TEAMS["NBA"] or away in TEAMS["NBA"]:
                print(f"Match d'intérêt trouvé : {away} @ {home}")
                # La NBA fournit souvent l'heure en ET (Eastern Time)
                # Format: 2026-04-27T19:30:00Z
                start_utc = datetime.fromisoformat(game['gameEt'].replace('Z', '+00:00'))
                
                games.append({
                    "league": "NBA 🏀",
                    "title": f"{away} @ {home}",
                    "desc": f"Séries NBA - {game.get('gameStatusText', 'À venir')}",
                    "start": start_utc
                })
    except Exception as e:
        print(f"Erreur NBA : {e}")
    return games

def generate_xml(all_games):
    print("--- Génération du fichier XMLTV ---")
    root = ET.Element("tv")
    
    # 1. Définition du Canal
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"
    # Optionnel : Ajoute un logo si tu as une URL
    # ET.SubElement(channel, "icon", src="URL_DE_TON_LOGO")

    # 2. Ajout des programmes
    if not all_games:
        print("Aucun match trouvé pour tes équipes. Création d'un bloc de repos.")
        now = datetime.now(pytz.UTC)
        stop = now + timedelta(hours=24)
        
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=stop.strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Pas de match prévu aujourd'hui"
        ET.SubElement(prog, "desc").text = "Tes équipes favorites sont au repos. Profites-en pour dormir !"
    else:
        for game in sorted(all_games, key=lambda x: x['start']):
            # Format XMLTV attendu : YYYYMMDDHHMMSS +HHMM
            start_str = game['start'].strftime("%Y%m%d%H%M%S +0000")
            # On estime la fin du match à 3h30 après le début
            stop_str = (game['start'] + timedelta(hours=3, minutes=30)).strftime("%Y%m%d%H%M%S +0000")
            
            prog = ET.SubElement(root, "programme", start=start_str, stop=stop_str, channel="Sports.Perso")
            ET.SubElement(prog, "title").text = f"{game['league']} | {game['title']}"
            ET.SubElement(prog, "desc").text = game['desc']
            ET.SubElement(prog, "category").text = "Sports"

    # 3. Sauvegarde
    tree = ET.ElementTree(root)
    # Utilisation d'une indentation pour que ce soit lisible
    ET.indent(tree, space="\t", level=0)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)
    print("Fichier epg_sports.xml généré avec succès.")

if __name__ == "__main__":
    combined_data = fetch_nhl() + fetch_nba()
    generate_xml(combined_data)
    
