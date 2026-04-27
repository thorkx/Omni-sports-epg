import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
MY_TEAMS = ["MTL", "COL", "UTA", "UTAH", "PHI", "PIT"] # Ajouté PHI/PIT pour valider que ça marche ce soir

def fetch_nhl_data():
    print("=== RÉCUPÉRATION DES MATCHS NHL (Format 2026) ===")
    games_list = []
    url = "https://api-web.nhle.com/v1/score/now"
    
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        
        for g in data.get('games', []):
            # LA CORRECTION EST ICI : on utilise 'abbrev'
            away_abbr = g.get('awayTeam', {}).get('abbrev', '???')
            home_abbr = g.get('homeTeam', {}).get('abbrev', '???')
            
            print(f"Analyse match : {away_abbr} @ {home_abbr}")

            # Filtrage par tes équipes
            if away_abbr in MY_TEAMS or home_abbr in MY_TEAMS:
                print(f"✅ MATCH MATCHÉ : {away_abbr} @ {home_abbr}")
                
                # Heure de début
                start_str = g.get('startTimeUTC')
                start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                
                # Description (Playoffs)
                series = g.get('seriesStatus', {})
                desc = f"Match {series.get('gameNumberOfSeries', '')} - {series.get('seriesTitle', 'NHL')}"
                
                games_list.append({
                    "title": f"🏒 {away_abbr} @ {home_abbr}",
                    "desc": desc,
                    "start": start_utc
                })

    except Exception as e:
        print(f"Erreur : {e}")
    
    return games_list

def generate_xml(games):
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"

    now = datetime.now(pytz.UTC)
    
    if not games:
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Aucun match favori aujourd'hui"
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
    print(f"Succès : {len(games)} matchs dans le XML.")

if __name__ == "__main__":
    data = fetch_nhl_data()
    generate_xml(data)
    
