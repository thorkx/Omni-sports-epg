import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION - MOTS CLÉS (Plus fiable que les codes)
# ==========================================
# Le script cherchera si ces mots sont présents dans le nom des équipes
MY_KEYWORDS = {
    "NHL": ["CANADIENS", "MONTREAL", "MTL", "AVALANCHE", "COLORADO", "COL"],
    "NBA": ["RAPTORS", "TORONTO", "TOR"]
}

def is_my_team(team_name, league):
    if not team_name: return False
    name_upper = team_name.upper()
    return any(keyword in name_upper for keyword in MY_KEYWORDS[league])

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data ---")
    games = []
    url = "https://api-web.nhle.com/v1/schedule/now"
    try:
        data = requests.get(url, timeout=10).json()
        for week in data.get('gameWeek', []):
            for game in week.get('games', []):
                # On récupère le nom complet ET l'abréviation pour être sûr
                home_name = game['homeTeam'].get('default', "")
                home_abbr = game['homeTeam'].get('abbreviation', "")
                away_name = game['awayTeam'].get('default', "")
                away_abbr = game['awayTeam'].get('abbreviation', "")
                
                if is_my_team(home_name, "NHL") or is_my_team(home_abbr, "NHL") or \
                   is_my_team(away_name, "NHL") or is_my_team(away_abbr, "NHL"):
                    
                    print(f"✅ Match NHL trouvé : {away_abbr} @ {home_abbr}")
                    start_utc = datetime.fromisoformat(game['startTimeUTC'].replace('Z', '+00:00'))
                    games.append({
                        "league": "NHL 🏒",
                        "title": f"{away_abbr} @ {home_abbr}",
                        "desc": f"Match NHL - {game.get('seriesSummary', {}).get('seriesStatusShort', 'Saison')}",
                        "start": start_utc
                    })
    except Exception as e:
        print(f"Erreur NHL : {e}")
    return games

def fetch_nba_week():
    print("--- Scraping NBA Weekly Data ---")
    games = []
    # Note: L'API Scoreboard de la NBA est très limitée au "jour même"
    url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
    try:
        data = requests.get(url, timeout=10).json()
        for game in data.get('scoreboard', {}).get('games', []):
            home_name = game['homeTeam']['teamName']
            home_abbr = game['homeTeam']['teamAbbreviation']
            away_name = game['awayTeam']['teamName']
            away_abbr = game['awayTeam']['teamAbbreviation']
            
            if is_my_team(home_name, "NBA") or is_my_team(home_abbr, "NBA") or \
               is_my_team(away_name, "NBA") or is_my_team(away_abbr, "NBA"):
                
                print(f"✅ Match NBA trouvé : {away_abbr} @ {home_abbr}")
                start_utc = datetime.fromisoformat(game['gameEt'].replace('Z', '+00:00'))
                games.append({
                    "league": "NBA 🏀",
                    "title": f"{away_abbr} @ {home_abbr}",
                    "desc": f"Match NBA - {game.get('gameStatusText', '')}",
                    "start": start_utc
                })
    except Exception as e:
        print(f"Erreur NBA : {e}")
    return games

def generate_xml(all_games):
    all_games.sort(key=lambda x: x['start'])
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"

    now = datetime.now(pytz.UTC)
    current_time = now

    if not all_games:
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Aucun match prévu"
        ET.SubElement(prog, "desc").text = "Vérifiez les mots-clés dans le script."
    else:
        for game in all_games:
            # On remplit le vide avant le match
            if game['start'] > current_time:
                wait_stop = game['start']
                prog_wait = ET.SubElement(root, "programme", 
                                         start=current_time.strftime("%Y%m%d%H%M%S +0000"), 
                                         stop=wait_stop.strftime("%Y%m%d%H%M%S +0000"), 
                                         channel="Sports.Perso")
                ET.SubElement(prog_wait, "title").text = f"⏳ Prochain : {game['title']}"
                ET.SubElement(prog_wait, "desc").text = f"Rendez-vous à {game['start'].astimezone(pytz.timezone('America/Toronto')).strftime('%H:%M')}"

            # Bloc du match
            match_stop = game['start'] + timedelta(hours=3, minutes=30)
            prog_match = ET.SubElement(root, "programme", 
                                      start=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                      stop=match_stop.strftime("%Y%m%d%H%M%S +0000"), 
                                      channel="Sports.Perso")
            ET.SubElement(prog_match, "title").text = f"{game['league']} | {game['title']}"
            ET.SubElement(prog_match, "desc").text = game['desc']
            
            current_time = match_stop

    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    combined = fetch_nhl_week() + fetch_nba_week()
    generate_xml(combined)
    
