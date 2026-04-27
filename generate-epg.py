import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION - AJOUT DE UTAH POUR TEST
# ==========================================
MY_KEYWORDS = {
    "NHL": ["MTL", "CANADIENS", "COL", "AVALANCHE", "UTA", "UTAH"],
    "NBA": ["TOR", "RAPTORS"]
}

def is_my_team(team_obj, league):
    # On fouille dans l'abréviation et le nom complet fourni par l'API
    search_space = [
        team_obj.get('abbreviation', '').upper(),
        team_obj.get('default', '').upper(),
        team_obj.get('placeName', {}).get('default', '').upper()
    ]
    return any(keyword in " ".join(search_space) for keyword in MY_KEYWORDS[league])

def fetch_nhl_today():
    print("--- Scraping NHL (Scoreboard Mode) ---")
    games = []
    # Cet URL est le plus fiable pour les matchs "Live" et du jour même
    url = "https://api-web.nhle.com/v1/score/now"
    try:
        data = requests.get(url, timeout=10).json()
        found_games = data.get('games', [])
        print(f"Total matchs NHL trouvés par l'API : {len(found_games)}")

        for game in found_games:
            home_team = game['homeTeam']
            away_team = game['awayTeam']
            
            # Debug: Affiche tous les matchs pour voir les noms d'équipes
            print(f"Scan : {away_team.get('abbreviation')} @ {home_team.get('abbreviation')}")

            if is_my_team(home_team, "NHL") or is_my_team(away_team, "NHL"):
                print(f"🎯 MATCH TROUVÉ : {away_team.get('abbreviation')} @ {home_team.get('abbreviation')}")
                
                # Conversion date
                start_utc = datetime.fromisoformat(game['startTimeUTC'].replace('Z', '+00:00'))
                
                games.append({
                    "league": "NHL 🏒",
                    "title": f"{away_team.get('abbreviation')} @ {home_team.get('abbreviation')}",
                    "desc": f"Match NHL - En direct de {game.get('venue', {}).get('default', 'l''aréna')}",
                    "start": start_utc
                })
    except Exception as e:
        print(f"Erreur NHL : {e}")
    return games

def generate_xml(all_games):
    all_games.sort(key=lambda x: x['start'])
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"

    now = datetime.now(pytz.UTC)
    current_time = now

    if not all_games:
        print("❌ Toujours aucun match trouvé dans la boucle finale.")
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Aucun match trouvé (Debug Utah)"
        ET.SubElement(prog, "desc").text = "Vérifie les logs GitHub Actions pour voir la liste des abréviations."
    else:
        for game in all_games:
            # Remplissage du vide avant
            if game['start'] > current_time:
                prog_wait = ET.SubElement(root, "programme", 
                                         start=current_time.strftime("%Y%m%d%H%M%S +0000"), 
                                         stop=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                         channel="Sports.Perso")
                ET.SubElement(prog_wait, "title").text = f"⏳ Prochain : {game['title']}"
                ET.SubElement(prog_wait, "desc").text = "Préparez le pop-corn !"

            # Le match
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
    # Test ciblé sur la NHL pour ce soir
    data = fetch_nhl_today()
    generate_xml(data)
    
