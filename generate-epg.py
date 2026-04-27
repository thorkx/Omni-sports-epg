import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
RANKING = ["MTL", "COL", "UTA", "PHI", "PIT", "TOR"]

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data (Fix TBD Text) ---")
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
                    
                    # Détection stricte de l'heure temporaire
                    is_tbd = "12:00:00Z" in start_str
                    
                    # Description
                    desc_parts = []
                    game_type = g.get('gameType')
                    if game_type == 3:
                        series = g.get('seriesStatus', {})
                        series_str = f"SÉRIES: ({series.get('topSeedTeamAbbrev')} {series.get('topSeedWins', 0)}-{series.get('bottomSeedWins', 0)} {series.get('bottomSeedTeamAbbrev')})"
                        desc_parts.append(series_str)
                    else:
                        desc_parts.append(f"Fiche: {away_abbr}({away_team.get('record', 'N/A')}) @ {home_abbr}({home_team.get('record', 'N/A')})")

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

    confirmed_games = [g for g in all_games if not g['is_tbd']]

    # Si aucun match n'est confirmé dans les prochaines 24h
    if not confirmed_games and all_games:
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Calendrier NHL (Heures TBD)"
        future_list = []
        for f in all_games:
            f_local = f['start'].astimezone(tz_quebec)
            # ICI: On force l'affichage TBD
            time_label = "TBD" if f['is_tbd'] else f_local.strftime('%H:%M')
            future_list.append(f"• {f_local.strftime('%d/%m')} {time_label} : {f['title']}")
        ET.SubElement(prog, "desc").text = "Matchs à venir :\n" + "\n".join(future_list)
    else:
        for i, game in enumerate(confirmed_games):
            # 1. Bloc d'attente
            if game['start'] > current_time:
                prog_wait = ET.SubElement(root, "programme", 
                                         start=current_time.strftime("%Y%m%d%H%M%S +0000"), 
                                         stop=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                         channel="Sports.Perso")
                ET.SubElement(prog_wait, "title").text = f"⏳ Prochain : {game['title']}"
                
                future_list = []
                for f in all_games:
                    if f['start'] >= current_time:
                        f_local = f['start'].astimezone(tz_quebec)
                        # ICI: Correction de l'affichage de l'heure
                        time_label = "TBD" if f['is_tbd'] else f_local.strftime('%H:%M')
                        future_list.append(f"• {f_local.strftime('%d/%m')} {time_label} : {f['title']}")
                
                ET.SubElement(prog_wait, "desc").text = "CALENDRIER DE LA SEMAINE :\n" + "\n".join(future_list)

            # 2. Bloc Match confirmé
            match_stop = game['start'] + timedelta(hours=3, minutes=30)
            prog_match = ET.SubElement(root, "programme", 
                                      start=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                      stop=match_stop.strftime("%Y%m%d%H%M%S +0000"), 
                                      channel="Sports.Perso")
            ET.SubElement(prog_match, "title").text = f"🏒 {game['title']}"
            ET.SubElement(prog_match, "desc").text = game['desc']
            current_time = match_stop

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl_week()
    generate_xml(data)
