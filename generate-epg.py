import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
RANKING = ["MTL", "COL", "UTA", "PHI", "PIT", "TOR"]

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data (TBD Deep Fix) ---")
    games = []
    url = "https://api-web.nhle.com/v1/schedule/now"
    tz_quebec = pytz.timezone('America/Toronto')
    
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        
        for week in data.get('gameWeek', []):
            for g in week.get('games', []):
                away_abbr = g.get('awayTeam', {}).get('abbrev')
                home_abbr = g.get('homeTeam', {}).get('abbrev')
                
                if away_abbr in RANKING or home_abbr in RANKING:
                    start_str = g.get('startTimeUTC', "")
                    start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    
                    # Conversion locale pour le test de détection
                    local_time = start_utc.astimezone(tz_quebec)
                    
                    # DÉTECTION RADICALE :
                    # Si l'heure locale est 08:00 AM, c'est un placeholder TBD de la NHL.
                    # On teste aussi le 12:00 UTC brut au cas où.
                    is_tbd = (local_time.hour == 8 and local_time.minute == 0) or (start_utc.hour == 12 and start_utc.minute == 0)
                    
                    print(f"Match: {away_abbr}@{home_abbr} | UTC: {start_utc.strftime('%H:%M')} | Local: {local_time.strftime('%H:%M')} | TBD: {is_tbd}")

                    # Description
                    desc_parts = []
                    if g.get('gameType') == 3:
                        s = g.get('seriesStatus', {})
                        desc_parts.append(f"SÉRIES: ({s.get('topSeedTeamAbbrev')} {s.get('topSeedWins')}-{s.get('bottomSeedWins')} {s.get('bottomSeedTeamAbbrev')})")
                    else:
                        desc_parts.append(f"Record: {away_abbr}({g.get('awayTeam',{}).get('record')}) @ {home_abbr}({g.get('homeTeam',{}).get('record')})")

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

    # Si pas de matchs confirmés, on affiche juste la liste TBD
    if not confirmed_games and all_games:
        prog = ET.SubElement(root, "programme", start=now.strftime("%Y%m%d%H%M%S +0000"), stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Calendrier NHL (TBD)"
        lines = []
        for f in all_games:
            f_l = f['start'].astimezone(tz_quebec)
            t_label = "TBD" if f['is_tbd'] else f_l.strftime('%H:%M')
            lines.append(f"• {f_l.strftime('%d/%m')} {t_label} : {f['title']}")
        ET.SubElement(prog, "desc").text = "\n".join(lines)
    else:
        for i, game in enumerate(confirmed_games):
            # Bloc d'attente
            if game['start'] > current_time:
                prog_wait = ET.SubElement(root, "programme", start=current_time.strftime("%Y%m%d%H%M%S +0000"), stop=game['start'].strftime("%Y%m%d%H%M%S +0000"), channel="Sports.Perso")
                ET.SubElement(prog_wait, "title").text = f"⏳ Prochain : {game['title']}"
                
                future_list = []
                for f in all_games:
                    if f['start'] >= current_time:
                        f_l = f['start'].astimezone(tz_quebec)
                        # LOGIQUE D'AFFICHAGE DU TEXTE TBD ICI
                        t_label = "TBD" if f['is_tbd'] else f_l.strftime('%H:%M')
                        future_list.append(f"• {f_l.strftime('%d/%m')} {t_label} : {f['title']}")
                ET.SubElement(prog_wait, "desc").text = "CALENDRIER :\n" + "\n".join(future_list)

            # Match confirmé
            stop = game['start'] + timedelta(hours=3, minutes=30)
            prog = ET.SubElement(root, "programme", start=game['start'].strftime("%Y%m%d%H%M%S +0000"), stop=stop.strftime("%Y%m%d%H%M%S +0000"), channel="Sports.Perso")
            ET.SubElement(prog, "title").text = f"🏒 {game['title']}"
            ET.SubElement(prog, "desc").text = game['desc']
            current_time = stop

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl_week()
    generate_xml(data)
    
