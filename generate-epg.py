import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
RANKING = ["MTL", "COL", "UTA", "PHI", "PIT", "TOR"]

def get_preview_text(game_data):
    """Génère un texte de contexte basé sur les leaders et l'état de la série."""
    series = game_data.get('seriesStatus', {})
    leaders = game_data.get('teamLeaders', [])
    
    # 1. Analyse de la forme (Leaders)
    top_performers = []
    for l in leaders:
        name = f"{l.get('firstName', {}).get('default')} {l.get('lastName', {}).get('default')}"
        cat = l.get('category')
        val = l.get('value')
        team = l.get('teamAbbrev')
        if cat == "goals" and val > 1:
            top_performers.append(f"{name} ({team}) a déjà {val} buts dans cette série.")
    
    perf_text = " ".join(top_performers[:2])
    
    # 2. Enjeux de la série
    win_lead = ""
    if series:
        if series.get('topSeedWins') > series.get('bottomSeedWins'):
            leader = series.get('topSeedTeamAbbrev')
            diff = series.get('topSeedWins') - series.get('bottomSeedWins')
            win_lead = f"{leader} domine la série et cherche à creuser l'écart."
        elif series.get('bottomSeedWins') > series.get('topSeedWins'):
            leader = series.get('bottomSeedTeamAbbrev')
            win_lead = f"{leader} a le momentum avec l'avance dans la série."
        else:
            win_lead = "Série égale : ce match est pivot pour briser l'impasse."

    # 3. Construction du paragraphe
    preview = f"🏒 ENJEUX : {win_lead} "
    if perf_text:
        preview += f"À SURVEILLER : {perf_text} "
    
    preview += "Blessures : Consultez les rapports de dernière minute."
    return preview

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data with Previews ---")
    games = []
    url = "https://api-web.nhle.com/v1/score/now" # On utilise score pour avoir les leaders
    try:
        data = requests.get(url, timeout=15).json()
        
        for g in data.get('games', []):
            away_abbr = g.get('awayTeam', {}).get('abbrev')
            home_abbr = g.get('homeTeam', {}).get('abbrev')
            
            if away_abbr in RANKING or home_abbr in RANKING:
                series = g.get('seriesStatus', {})
                game_num = series.get('gameNumberOfSeries', 0)
                
                # État de la série
                top_w = series.get('topSeedWins', 0)
                bot_w = series.get('bottomSeedWins', 0)
                series_str = f"({series.get('topSeedTeamAbbrev')} {top_w}-{bot_w} {series.get('bottomSeedTeamAbbrev')})"

                # Diffuseurs
                tv_list = g.get('tvBroadcasts', [])
                ca_tv = [tv['network'] for tv in tv_list if tv['countryCode'] == 'CA']
                tv_str = f"📺 {', '.join(ca_tv) if ca_tv else 'Poste à confirmer'}"

                # GÉNÉRATION DU TEXTE AUTOMATIQUE
                preview_text = get_preview_text(g)

                start_str = g.get('startTimeUTC', "")
                is_tbd = "12:00:00Z" in start_str
                start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                
                games.append({
                    "league": "NHL 🏒",
                    "title": f"{away_abbr} @ {home_abbr}",
                    "desc": f"{series_str} | {tv_str}\n\n{preview_text}",
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

    for i, game in enumerate(all_games):
        # Bloc d'attente
        if game['start'] > current_time:
            prog_wait = ET.SubElement(root, "programme", 
                                     start=current_time.strftime("%Y%m%d%H%M%S +0000"), 
                                     stop=game['start'].strftime("%Y%m%d%H%M%S +0000"), 
                                     channel="Sports.Perso")
            ET.SubElement(prog_wait, "title").text = f"⏳ Prochain : {game['title']}"
            # On met le preview du prochain match dans le bloc d'attente !
            ET.SubElement(prog_wait, "desc").text = f"PRÉVIEW : {game['desc']}"

        # Bloc Match
        stop = game['start'] + timedelta(hours=3, minutes=30)
        prog = ET.SubElement(root, "programme", start=game['start'].strftime("%Y%m%d%H%M%S +0000"), stop=stop.strftime("%Y%m%d%H%M%S +0000"), channel="Sports.Perso")
        ET.SubElement(prog, "title").text = f"{game['league']} | {game['title']}"
        ET.SubElement(prog, "desc").text = game['desc']
        current_time = stop

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl_week()
    generate_xml(data)
    
