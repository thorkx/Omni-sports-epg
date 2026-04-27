import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
RANKING = ["MTL", "COL", "UTA", "BUF"]

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data (TBD Fix: 16:00 UTC) ---")
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
                    
                    # DÉTECTION TBD (16:00 UTC = 12:00 LOCAL)
                    # On couvre 12:00 UTC et 16:00 UTC pour être certains
                    is_tbd = (start_utc.hour == 16 and start_utc.minute == 0) or \
                             (start_utc.hour == 12 and start_utc.minute == 0)
                    
                    # Description simple
                    desc_parts = []
                    if g.get('gameType') == 3:
                        s = g.get('seriesStatus', {})
                        desc_parts.append(f"SÉRIES: ({s.get('topSeedTeamAbbrev')} {s.get('topSeedWins')}-{s.get('bottomSeedWins')} {s.get('bottomSeedTeamAbbrev')})")
                    else:
                        desc_parts.append(f"Fiche: {away_abbr}({g.get('awayTeam',{}).get('record')}) @ {home_abbr}({g.get('homeTeam',{}).get('record')})")

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

    # Filtrage : Seuls les matchs avec heure confirmée créent un bloc de temps
    confirmed_games = [g for g in all_games if not g['is_tbd']]

    for i, game in enumerate(confirmed_games):
        # 1. Bloc d'attente (liste complète incluant les TBD)
        if game['start'] > current_time:
            prog_wait = ET.SubElement(root, "programme", 
                                     start=current_time.strftime("%Y%m%d%H%M%S +0000"), 
                                     stop=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                     channel="Sports.Perso")
            ET.SubElement(prog_wait, "title").text = f"⏳ Prochain : {game['title']}"
            
            lines = []
            for f in all_games:
                if f['start'] >= current_time:
                    f_local = f['start'].astimezone(tz_quebec)
                    # AFFICHAGE FORCE TBD SI is_tbd est True
                    t_label = "TBD" if f['is_tbd'] else f_local.strftime('%H:%M')
                    lines.append(f"• {f_local.strftime('%d/%m')} {t_label} : {f['title']}")
            ET.SubElement(prog_wait, "desc").text = "CALENDRIER :\n" + "\n".join(lines)

        # 2. Bloc Match confirmé
        stop = game['start'] + timedelta(hours=3, minutes=30)
        prog = ET.SubElement(root, "programme", 
                             start=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                             stop=stop.strftime("%Y%m%d%H%M%S +0000"), 
                             channel="Sports.Perso")
        ET.SubElement(prog, "title").text = f"🏒 {game['title']}"
        ET.SubElement(prog, "desc").text = game['desc']
        current_time = stop

    # Cas de secours si aucun match n'est confirmé
    if not confirmed_games and all_games:
        prog = ET.SubElement(root, "programme", start=now.strftime("%Y%m%d%H%M%S +0000"), stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Calendrier NHL (TBD)"
        lines = [f"• {f['start'].astimezone(tz_quebec).strftime('%d/%m')} TBD : {f['title']}" for f in all_games]
        ET.SubElement(prog, "desc").text = "\n".join(lines)

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl_week()
    generate_xml(data)
    
