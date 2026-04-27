import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
TEAMS = {
    "NHL": ["MTL", "COL"], 
    "NBA": ["TOR"]
}

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data ---")
    games = []
    # Cet URL donne les matchs de la semaine en cours
    url = "https://api-web.nhle.com/v1/schedule/now"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        for week in data.get('gameWeek', []):
            for game in week.get('games', []):
                home = game['homeTeam']['abbreviation'].upper()
                away = game['awayTeam']['abbreviation'].upper()
                
                if home in TEAMS["NHL"] or away in TEAMS["NHL"]:
                    print(f"✅ Match NHL trouvé : {away} @ {home} le {game['gameDate']}")
                    start_utc = datetime.fromisoformat(game['startTimeUTC'].replace('Z', '+00:00'))
                    
                    games.append({
                        "league": "NHL 🏒",
                        "title": f"{away} @ {home}",
                        "desc": f"Match de saison/playoffs NHL à {game.get('venue', {}).get('default', 'l''aréna')}",
                        "start": start_utc
                    })
    except Exception as e:
        print(f"Erreur NHL : {e}")
    return games

def fetch_nba_week():
    print("--- Scraping NBA Weekly Data ---")
    games = []
    # La NBA est plus complexe par jour, on va donc itérer sur les 7 prochains jours
    base_url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
    # Note: Pour une version simplifiée, on garde le scoreboard du jour. 
    # Pour le calendrier complet NBA, l'API stats.nba est préférable mais nécessite des headers complexes.
    try:
        response = requests.get(base_url, timeout=10)
        data = response.json()
        for game in data.get('scoreboard', {}).get('games', []):
            home = game['homeTeam']['teamAbbreviation'].upper()
            away = game['awayTeam']['teamAbbreviation'].upper()
            
            if home in TEAMS["NBA"] or away in TEAMS["NBA"]:
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
    all_games.sort(key=lambda x: x['start'])
    print(f"--- Génération XML : {len(all_games)} match(s) au calendrier ---")
    
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"

    now = datetime.now(pytz.UTC)

    if not all_games:
        # Bloc par défaut
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Aucun match cette semaine"
        ET.SubElement(prog, "desc").text = "Repos complet pour vos équipes."
    else:
        # LOGIQUE DE REMPLISSAGE (FILL GAPS)
        # On crée un bloc "En attente" entre maintenant et le premier match
        current_time = now
        
        for game in all_games:
            # Si le match est dans le futur, on remplit le vide avant
            if game['start'] > current_time:
                wait_prog = ET.SubElement(root, "programme", 
                                         start=current_time.strftime("%Y%m%d%H%M%S +0000"), 
                                         stop=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                         channel="Sports.Perso")
                ET.SubElement(wait_prog, "title").text = f"⏳ Prochain : {game['title']}"
                ET.SubElement(wait_prog, "desc").text = f"Le prochain rendez-vous {game['league']} est à {game['start'].astimezone(pytz.timezone('America/Toronto')).strftime('%H:%M')}"

            # Le bloc du match lui-même
            match_stop = game['start'] + timedelta(hours=3, minutes=30)
            prog = ET.SubElement(root, "programme", 
                                 start=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                 stop=match_stop.strftime("%Y%m%d%H%M%S +0000"), 
                                 channel="Sports.Perso")
            ET.SubElement(prog, "title").text = f"{game['league']} | {game['title']}"
            ET.SubElement(prog, "desc").text = game['desc']
            
            # On avance le curseur de temps à la fin du match
            current_time = match_stop

    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl_week() + fetch_nba_week()
    generate_xml(data)
    
