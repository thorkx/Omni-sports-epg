import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
# L'ordre dans cette liste définit la priorité d'affichage (MTL en premier)
RANKING = ["MTL", "COL", "UTA", "PHI", "PIT", "TOR"]

CANADIAN_NETWORKS = ["RDS", "RDS2", "TVAS", "TVAS2", "SN", "SNE", "SNO", "SNW", "SNP", "SN360", "CBC"]

def get_priority(abbr):
    try:
        return RANKING.index(abbr)
    except ValueError:
        return 999

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data ---")
    games = []
    url = "https://api-web.nhle.com/v1/schedule/now"
    try:
        data = requests.get(url, timeout=15).json()
        
        for week in data.get('gameWeek', []):
            for g in week.get('games', []):
                away_abbr = g.get('awayTeam', {}).get('abbrev')
                home_abbr = g.get('homeTeam', {}).get('abbrev')
                
                if away_abbr in RANKING or home_abbr in RANKING:
                    # 1. État de la série
                    series = g.get('seriesStatus', {})
                    status_str = ""
                    if series:
                        top = series.get('topSeedTeamAbbrev')
                        bot = series.get('bottomSeedTeamAbbrev')
                        top_w = series.get('topSeedWins', 0)
                        bot_w = series.get('bottomSeedWins', 0)
                        status_str = f"({top} {top_w}-{bot_w} {bot})"

                    # 2. Diffuseurs (Priorité Canada)
                    tv_list = g.get('tvBroadcasts', [])
                    ca_tv = [tv['network'] for tv in tv_list if tv['countryCode'] == 'CA']
                    other_tv = [tv['network'] for tv in tv_list if tv['countryCode'] != 'CA']
                    final_tv = ca_tv + other_tv
                    tv_str = f"📺 {', '.join(final_tv)}" if final_tv else "📺 Non annoncé"

                    start_utc = datetime.fromisoformat(g['startTimeUTC'].replace('Z', '+00:00'))
                    
                    games.append({
                        "league": "NHL 🏒",
                        "home": home_abbr,
                        "away": away_abbr,
                        "title": f"{away_abbr} @ {home_abbr}",
                        "desc": f"{status_str} {tv_str}".strip(),
                        "start": start_utc,
                        "priority": min(get_priority(home_abbr), get_priority(away_abbr))
                    })
    except Exception as e:
        print(f"Erreur : {e}")
    return games

def generate_xml(all_games):
    # Tri par date, puis par priorité d'équipe
    all_games.sort(key=lambda x: (x['start'], x['priority']))
    
    root = ET.Element("tv")
    channel = ET.SubElement(root, "channel", id="Sports.Perso")
    ET.SubElement(channel, "display-name").text = "Mon Omni-Sports"

    now = datetime.now(pytz.UTC)
    current_time = now

    if not all_games:
        prog = ET.SubElement(root, "programme", start=now.strftime("%Y%m%d%H%M%S +0000"), stop=(now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000"), channel="Sports.Perso")
        ET.SubElement(prog, "title").text = "📅 Aucun match cette semaine"
    else:
        for i, game in enumerate(all_games):
            # Bloc d'attente (Pre-match)
            if game['start'] > current_time:
                # Dans la description du bloc d'attente, on liste les prochains matchs
                future_matches = []
                for f in all_games[i:]:
                    time_str = f['start'].astimezone(pytz.timezone('America/Toronto')).strftime('%H:%M')
                    future_matches.append(f"• {time_str} : {f['title']}")
                
                prog_wait = ET.SubElement(root, "programme", 
                                         start=current_time.strftime("%Y%m%d%H%M%S +0000"), 
                                         stop=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                         channel="Sports.Perso")
                ET.SubElement(prog_wait, "title").text = f"⏳ Prochain : {game['title']}"
                ET.SubElement(prog_wait, "desc").text = "\n".join(future_matches)

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
    ET.indent(tree)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl_week()
    generate_xml(data)
    
