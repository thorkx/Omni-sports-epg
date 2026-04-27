import requests
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURATION
# ==========================================
RANKING = ["MTL", "COL", "UTA", "PHI", "PIT", "TOR"]

def get_streak(team_data):
    """Extrait la séquence (ex: W3, L1)"""
    streak_code = team_data.get('streakCode', '')
    streak_count = team_data.get('streakCount', '')
    return f"{streak_code}{streak_count}" if streak_code else "N/A"

def fetch_nhl_week():
    print("--- Scraping NHL Weekly Data Enhanced ---")
    games = []
    # On utilise schedule pour la vision hebdomadaire
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
                    # 1. Infos de base
                    start_str = g.get('startTimeUTC', "")
                    start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    is_tbd = "12:00:00Z" in start_str
                    
                    # 2. Logique de description dynamique
                    desc_parts = []
                    game_type = g.get('gameType') # 2 = Saison, 3 = Playoffs
                    
                    if game_type == 3: # PLAYOFFS
                        series = g.get('seriesStatus', {})
                        game_num = series.get('gameNumberOfSeries', 0)
                        top_w = series.get('topSeedWins', 0)
                        bot_w = series.get('bottomSeedWins', 0)
                        
                        # État de la série
                        desc_parts.append(f"SÉRIES : Match #{game_num} ({series.get('topSeedTeamAbbrev')} {top_w}-{bot_w} {series.get('bottomSeedTeamAbbrev')})")
                        
                        # Si ce n'est pas le match 1, on mentionne le dernier résultat (souvent dans l'objet series)
                        if game_num > 1:
                            # Note: L'API schedule donne peu de détails sur le match 'précédent' spécifique, 
                            # on mise sur l'état de la série qui est l'info la plus fraîche.
                            desc_parts.append("Dernier match: Voir les faits saillants récents.")
                    
                    else: # SAISON RÉGULIÈRE
                        # Séquences
                        away_streak = get_streak(away_team)
                        home_streak = get_streak(home_team)
                        desc_parts.append(f"Séquences : {away_abbr}({away_streak}) | {home_abbr}({home_streak})")
                        
                        # Record tête-à-tête (si disponible dans l'API)
                        # À défaut d'historique complet, on indique les fiches générales
                        desc_parts.append(f"Fiches : {away_abbr}({away_team.get('record', 'N/A')}) - {home_abbr}({home_team.get('record', 'N/A')})")

                    # 3. Diffuseurs
                    tv_list = g.get('tvBroadcasts', [])
                    ca_tv = [tv['network'] for tv in tv_list if tv['countryCode'] == 'CA']
                    tv_str = f"📺 {', '.join(ca_tv)}" if ca_tv else "📺 Heure/Poste à confirmer"

                    full_desc = " | ".join(desc_parts) + "\n" + tv_str
                    
                    games.append({
                        "league": "NHL 🏒",
                        "title": f"{away_abbr} @ {home_abbr}",
                        "desc": full_desc,
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
            
            # Titre du bloc d'attente
            wait_title = f"⏳ Prochain : {game['title']}"
            if game['is_tbd']: wait_title += " (TBD)"
            ET.SubElement(prog_wait, "title").text = wait_title
            
            # On liste les prochains matchs dans la description
            future_list = []
            for f in all_games[i:]:
                f_time = f['start'].astimezone(pytz.timezone('America/Toronto')).strftime('%d/%m %H:%M')
                future_list.append(f"• {f_time} : {f['title']}")
            ET.SubElement(prog_wait, "desc").text = "\n".join(future_list)

        # Bloc Match
        stop = game['start'] + timedelta(hours=3, minutes=30)
        prog = ET.SubElement(root, "programme", start=game['start'].strftime("%Y%m%d%H%M%S +0000"), stop=stop.strftime("%Y%m%d%H%M%S +0000"), channel="Sports.Perso")
        
        display_title = f"{game['league']} | {game['title']}"
        if game['is_tbd']: display_title += " (HEURE TBD)"
            
        ET.SubElement(prog, "title").text = display_title
        ET.SubElement(prog, "desc").text = game['desc']
        current_time = stop

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write("epg_sports.xml", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    data = fetch_nhl_week()
    generate_xml(data)
    
