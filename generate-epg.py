import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
RANKING = ["MTL", "COL", "UTA", "PHI", "PIT", "TOR"]

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data (Robust TBD Detection) ---")
    games = []
    url = "https://api-web.nhle.com/v1/schedule/now"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        
        for week in data.get('gameWeek', []):
            for g in week.get('games', []):
                away_abbr = g.get('awayTeam', {}).get('abbrev')
                home_abbr = g.get('homeTeam', {}).get('abbrev')
                
                if away_abbr in RANKING or home_abbr in RANKING:
                    start_str = g.get('startTimeUTC', "")
                    # Conversion en objet datetime pour une analyse précise
                    start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    
                    # DÉTECTION ROBUSTE : 
                    # L'heure TBD de la NHL est TOUJOURS 12:00:00 UTC (8h00 AM EDT)
                    # On vérifie l'heure et la minute sur l'objet datetime directement
                    is_tbd = (start_utc.hour == 12 and start_utc.minute == 0)
                    
                    if is_tbd:
                        print(f"Match TBD détecté logiquement : {away_abbr} @ {home_abbr}")

                    # Description
                    desc_parts = []
                    game_type = g.get('gameType')
                    if game_type == 3:
                        series = g.get('seriesStatus', {})
                        series_str = f"SÉRIES: ({series.get('topSeedTeamAbbrev')} {series.get('topSeedWins', 0)}-{series.get('bottomSeedWins', 0)} {series.get('bottomSeedTeamAbbrev')})"
                        desc_parts.append(series_str)
                    else:
                        away_rec = g.get('awayTeam', {}).get('record', 'N/A')
                        home_rec = g.get('homeTeam', {}).get('record', 'N/A')
                        desc_parts.append(f"Fiche: {away_abbr}({away_rec}) @ {home_abbr}({home_rec})")

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

    # Cas où aucun match n'est confirmé (que des TBD)
    if not confirmed_games and all_games:
        prog = ET.SubElement(root, "programme", 
                             start=now.strftime("%Y%m%d%H%M%S +0000"), 
                             stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Calendrier NHL (Heures TBD)"
        future_list = []
        for f in all_games:
            f_local = f['start'].astimezone(tz_quebec)
            time_label = "TBD" if f['is_tbd'] else f_local.strftime('%H:%M')
            future_list.append(f"• {f_local.strftime('%d/%m')} {time_label} : {f['title']}")
        ET.SubElement(prog, "desc").text = "Prochains matchs :\n" + "\n".join(future_list)
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
    
