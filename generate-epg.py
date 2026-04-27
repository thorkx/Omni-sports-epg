import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# Configuration des équipes
TEAMS = {"NHL": ["MTL", "COL"], "NBA": ["TOR"]}

def fetch_nhl():
    games = []
    url = "https://api-web.nhle.com/v1/schedule/now"
    try:
        data = requests.get(url).json()
        for week in data.get('gameWeek', []):
            for game in week.get('games', []):
                home = game['homeTeam']['abbreviation']
                away = game['awayTeam']['abbreviation']
                if home in TEAMS["NHL"] or away in TEAMS["NHL"]:
                    start_utc = datetime.strptime(game['startTimeUTC'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
                    games.append({
                        "league": "NHL 🏒",
                        "title": f"{away} @ {home}",
                        "desc": f"Match NHL - {away} contre {home}",
                        "start": start_utc
                    })
    except: pass
    return games

def fetch_nba():
    games = []
    # Utilisation de l'API CDN de la NBA (plus stable pour les scripts)
    url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
    try:
        data = requests.get(url).json()
        scoreboard = data.get('scoreboard', {})
        for game in scoreboard.get('games', []):
            home = game['homeTeam']['teamAbbreviation']
            away = game['awayTeam']['teamAbbreviation']
            if home in TEAMS["NBA"] or away in TEAMS["NBA"]:
                # Format: 2024-04-27T23:00:00Z
                start_utc = datetime.strptime(game['gameEt'], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.timezone("America/New_York"))
                games.append({
                    "league": "NBA 🏀",
                    "title": f"{away} @ {home}",
                    "desc": f"Séries NBA - {game['gameStatusText']}",
                    "start": start_utc.astimezone(pytz.UTC)
                })
    except: pass
    return games

def generate_xml(all_games):
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"

    for game in sorted(all_games, key=lambda x: x['start']):
        # On crée un bloc de 3h pour chaque match
        start_fmt = game['start'].strftime("%Y%m%d%H%M%S %z").replace(" ", "")
        stop_fmt = (game['start'] + timedelta(hours=3)).strftime("%Y%m%d%H%M%S %z").replace(" ", "")
        
        prog = ET.SubElement(root, "programme", start=start_fmt, stop=stop_fmt, channel="Sports.Perso")
        ET.SubElement(prog, "title").text = f"{game['league']} {game['title']}"
        ET.SubElement(prog, "desc").text = game['desc']

    tree = ET.ElementTree(root)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl() + fetch_nba()
    generate_xml(data)
  
