from flask import Flask, request, jsonify, render_template
import statsapi
from functools import lru_cache
from flask_cors import CORS


# All hitting stats work

app = Flask(__name__)
CORS(app)

@lru_cache(maxsize=128)
def getPlayerId(player_name):
    players = statsapi.lookup_player(player_name)
    if not players:
        return None
    return players[0].get('id')

def getPlayerStats(player_name, stat_type):
    player_id = getPlayerId(player_name)
    if not player_id:
        return None
    return statsapi.player_stat_data(player_id, group=stat_type, season='2025')

def getGamesPlayed(player_stats):
    stats = player_stats.get('stats', [])
    if stats and isinstance(stats[0], dict):
        games_played = stats[0].get('stats', {}).get('gamesPlayed', 0)
    else:
        games_played = 0
    games_remaining = 162 - games_played
    return games_played, games_remaining

def calculatePace(games_played, value):
    if games_played == 0:
        return 0
    return round((value / games_played) * 162)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/project', methods=['GET'])
def project():
    player = request.args.get('player')
    stat = request.args.get('stat')

    if not player or not stat:
        return jsonify({"error": "Missing player or stat"}), 400

    if stat == 'home runs' or stat == 'hits' or stat == 'walks' or stat == 'rbi' or stat == 'stolen bases':
        stat_type = 'hitting'
    elif stat == 'strikeouts':
        stat_type = 'pitching'

    player_stats = getPlayerStats(player, stat_type)
    if not player_stats:
        return jsonify({"error": "Player not found"}), 404

    stats = player_stats.get('stats', [])
    if not stats or not isinstance(stats[0], dict):
        return jsonify({"error": "Stats not available"}), 404

    game_stats = stats[0].get('stats', {})
    games_played, _ = getGamesPlayed(player_stats)

    # Hitting: Home runs, walks, hits, rbi, stolen bases, total bases, WAR
    # Pitching: Strikeouts, walks, hits, home runs allowed

    stat = stat.lower()
    if stat == "home runs":
        value = game_stats.get("homeRuns", 0)
    elif stat == "hits":
        value = game_stats.get("hits", 0)
    elif stat == "walks":
        value = game_stats.get("baseOnBalls", 0) + game_stats.get("intentionalWalks", 0)
    elif stat == "rbi":
        value = game_stats.get("rbi", 0)
    elif stat == "stolen bases":
        value = game_stats.get("stolenBases", 0)
    elif stat == "strikeouts":
        value == game_stats.get("strikeouts", 0)
    else:
        return jsonify({"error": "Unsupported stat"}), 400

    pace = calculatePace(games_played, value)
    return jsonify({
        "player": player.title(),
        "stat": stat,
        "pace": pace
    })

if __name__ == '__main__':
    app.run(debug=True)
