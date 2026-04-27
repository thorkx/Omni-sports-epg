import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

def fetch_all_nhl():
    print("=== SYNCHRONISATION NIVEAU 2 (DEEP SCAN) ===")
    games_list = []
    url = "https://api-web.nhle.com/v1/score/now"
    
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        
        for g in data.get('games', []):
            # On tente plusieurs clés pour l'équipe à l'extérieur
            away_team = g.get('awayTeam', {})
            away_name = away_team.get('abbreviation') or away_team.get('default') or "AWAY"
            
            # On tente plusieurs clés pour l'équipe à domicile
            home_team = g.get('homeTeam', {})
            home_name = home_team.get('abbreviation') or home_team.get('default') or "HOME"
            
            print(f"Match détecté : {away_name} @ {home_name}")
            
            # Gestion de l'heure
            start_str = g.get('startTimeUTC')
            if start_str:
                start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            else:
                start_utc = datetime.now(pytz.UTC)

            games_list.append({
                "title": f"🏒 {away_name} @ {home_name}",
                "desc": f"Match NHL - {away_name} contre {home_name}",
                "start": start_utc
            })

    except Exception as e:
        print(f"Erreur lors de l'extraction : {e}")
    
    return games_list

def generate_xml(games):
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Omni Sports Debug"

    if not games:
        now = datetime.now(pytz.UTC)
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "⚠️ Liste de matchs vide"
    else:
        for g in games:
            start_str = g['start'].strftime("%Y%m%d%H%M%S +0000")
            stop_str = (g['start'] + timedelta(hours=4)).strftime("%Y%m%d%H%M%S +0000")
            
            prog = ET.SubElement(root, "programme", start=start_str, stop=stop_str, channel="Sports.Perso")
            ET.SubElement(prog, "title").text = g['title']
            ET.SubElement(prog, "desc").text = g['desc']

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    found_games = fetch_all_nhl()
    generate_xml(found_games)
    
