import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

def fetch_all_nhl():
    print("=== SYNCHRONISATION TOTALE NHL ===")
    games_list = []
    url = "https://api-web.nhle.com/v1/score/now"
    
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        
        # On prend TOUS les matchs retournés par l'API sans exception
        for g in data.get('games', []):
            away = g.get('awayTeam', {}).get('abbreviation', '???')
            home = g.get('homeTeam', {}).get('abbreviation', '???')
            
            # Debug pour confirmer ce qu'on capture
            print(f"Capture du match : {away} @ {home}")
            
            # Conversion de l'heure UTC
            start_utc = datetime.fromisoformat(g['startTimeUTC'].replace('Z', '+00:00'))
            
            games_list.append({
                "title": f"🏒 {away} @ {home}",
                "desc": f"Match NHL diffusé le {start_utc.astimezone(pytz.timezone('America/Toronto')).strftime('%d/%m')}",
                "start": start_utc
            })

    except Exception as e:
        print(f"Erreur lors de la capture : {e}")
    
    return games_list

def generate_xml(games):
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Omni Sports Debug"

    if not games:
        # Message de secours si l'API est vraiment vide
        now = datetime.now(pytz.UTC)
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "⚠️ API NHL vide aujourd'hui"
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
    print(f"Succès : {len(games)} matchs écrits dans epg_sports.xml")

if __name__ == "__main__":
    found_games = fetch_all_nhl()
    generate_xml(found_games)
    
