import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
RANKING = ["MTL", "COL", "UTA", "PHI", "PIT", "TOR"]

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data (Clean Version) ---")
    games = []
    url = "https://api-web.nhle.com/v1/schedule/now"
    try:
        data = requests.get(url, timeout=15).json()
        
        for week in data.get('gameWeek', []):
            for g in week.get('games', []):
                away_team = g.get('awayTeam', {})
                home_team = g.get('homeTeam', {})
                away_abbr = away_team.get('abbrev')
                home_abbr = home_team.get('abbrev')
                
                if away_abbr in RANKING or home_abbr in RANKING:
                    start_str = g.get('startTimeUTC', "")
                    start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    
                    # Détection de l'heure temporaire (12:00 UTC)
                    is_tbd = "12:00:00Z" in start_str
                    
                    # Construction de la description simple
                    desc_parts = []
                    game_type = g.get('gameType')
                    
                    if game_type == 3: # SÉRIES
                        series = g.get('seriesStatus', {})
                        series_str = f"SÉRIES: ({series.get('topSeedTeamAbbrev')} {series.get('topSeedWins', 0)}-{series.get('bottomSeedWins', 0)} {series.get('bottomSeedTeamAbbrev')})"
                        desc_parts.append(series_str)
                    else: # SAISON
                        desc_parts.append(f"Record: {away_abbr}({away_team.get('record', 'N/A')}) @ {home_abbr}({home_team.get('record', 'N/A')})")

                    tv_list = g.get('tvBroadcasts', [])
                    ca_tv = [tv['network'] for tv in tv_list if tv['countryCode'] == 'CA']
                    if ca_tv: desc_parts.append(f"📺 {', '.join(ca_tv)}")

                    games.append({
                        "title": f"{away_abbr} @ {home_abbr}",
                        "desc": " | ".join(desc_parts),
                        "start": start_utc,
                        "is_tbd": is_tbd,
                        "priority": min(RANKING.index(home_abbr) if home_abbr in RANKING else 99, 
                                        RANKING.index(away_abbr) if away_abbr in RANKING else 99)
                    })
    except Exception as e:
        print(f"Erreur : {e}")
    return games

def generate_xml(all_games):
    all_games.sort(key=lambda x: (x['start'], x['priority']))
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"

    now = datetime.now(pytz.UTC)
    current_time = now
    tz_quebec = pytz.timezone('America/Toronto')

    # Filtrer pour n'avoir que les matchs avec une heure confirmée pour les blocs de programme
    confirmed_games = [g for g in all_games if not g['is_tbd']]

    for i, game in enumerate(confirmed_games):
        # Bloc d'attente entre les matchs
        if game['start'] > current_time:
            prog_wait = ET.SubElement(root, "programme", 
                                     start=current_time.strftime("%Y%m%d%H%M%S +0000"), 
                                     stop=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                     channel="Sports.Perso")
            ET.SubElement(prog_wait, "title").text = f"⏳ Prochain : {game['title']}"
            
            # Liste exhaustive (incluant les TBD) dans la description du bloc d'attente
            future_list = []
            for f in all_games:
                if f['start'] >= current_time:
                    f_local = f['start'].astimezone(tz_quebec)
                    time_label = "TBD" if f['is_tbd'] else f_local.strftime('%H:%M')
                    future_list.append(f"• {f_local.strftime('%d/%m')} {time_label} : {f['title']}")
            
            ET.SubElement(prog_wait, "desc").text = "CALENDRIER À VENIR :\n" + "\n".join(future_list)

        # Bloc du Match (Heure confirmée seulement)
        match_stop = game['start'] + timedelta(hours=3, minutes=30)
        prog = ET.SubElement(root, "programme", 
                             start=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                             stop=match_stop.strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = f"🏒 {game['title']}"
        ET.SubElement(prog, "desc").text = game['desc']
        current_time = match_stop

    # Si aucun match confirmé n'est trouvé, on crée un bloc "Calendrier" permanent
    if not confirmed_games:
        prog = ET.SubElement(root, "programme", start=now.strftime("%Y%m%d%H%M%S +0000"), stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Calendrier NHL (Heures à confirmer)"
        future_list = [f"• {f['start'].astimezone(tz_quebec).strftime('%d/%m')} TBD : {f['title']}" for f in all_games]
        ET.SubElement(prog, "desc").text = "\n".join(future_list) if future_list else "Aucun match prévu."

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl_week()
    generate_xml(data)
    
