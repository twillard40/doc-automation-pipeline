from smolagents import tool
import requests

# ============================================================
# UTILITIES
# ============================================================

# call_mlb_api()
def call_mlb_api(url: str) -> dict | None:
    """
    Makes a GET request to the MLB Stats API.
    Returns the JSON response as a dictionary, or None if the request fails.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        return None
    except requests.exceptions.ConnectionError:
        print("Connection error -- check your internet connection")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# get_player_id()
def get_player_id(player_name: str) -> int | list | None:
    """
    Looks up a player's mlbID from the MLB Stats API.
    Returns the mlbID as an integer, or None if the player is not found.
    """
    url = f"https://statsapi.mlb.com/api/v1/people/search?names={player_name}&sportId=1"
    data = call_mlb_api(url)
    
    if data is None or not data.get('people'):
        return None
    
    people = data['people']
    
    if len(people) > 1:
        return [p['fullName'] for p in people]
    
    return people[0]['id']

# get_pitcher_id()
def get_pitcher_id(player_name: str) -> int | list | None:
    """
    Looks up a pitcher's mlbID from the MLB Stats API.
    Returns the mlbID as an integer, or None if the pitcher is not found.
    """
    url = f"https://statsapi.mlb.com/api/v1/people/search?names={player_name}&sportId=1"
    data = call_mlb_api(url)
    
    if data is None or not data.get('people'):
        return None
    
    people = data['people']
    
    if len(people) > 1:
        return [p['fullName'] for p in people]
    
    return people[0]['id']

# ============================================================
# BATTING TOOLS
# ============================================================

# get_player_splits()
@tool
def get_player_splits(player_name: str, split_code: str) -> dict | str:
    """
    Retrieves batting split stats for a player against a specific situation.
    Use this when the user asks how a batter performs against left or right handed pitchers,
    at home or away, on the road, during day or night games, or any other split situation.

    Args:
        player_name: The full or partial name of the batter. Example: 'Ohtani' or 'Shohei Ohtani'.
        split_code: The situation code for the split. Common codes:
            vl = vs Left handed pitchers
            vr = vs Right handed pitchers
            h = Home games
            a = Away games, road games, on the road
            d = Day games
            n = Night games

    Returns:
        A dictionary with the player's stats for that split situation,
        or a string message explaining why data is not available.
    """
    player_id = get_player_id(player_name)

    if player_id is None:
        return f"No player found matching '{player_name}'. Check the spelling and try again."

    if isinstance(player_id, list):
        names = ", ".join(player_id)
        return f"Multiple players found matching '{player_name}': {names}. Please be more specific."

    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=statSplits&season=2026&group=hitting&sitCodes={split_code}"
    data = call_mlb_api(url)

    if data is None:
        return f"Could not retrieve data for {player_name}. The MLB Stats API may be unavailable."

    splits = data['stats'][0]['splits']

    if not splits:
        return f"No split data found for '{player_name}' with split code '{split_code}'."

    split = splits[0]
    stat = split['stat']
    description = split['split']['description']

    return {
        "player": player_name,
        "split": description,
        "avg": float(stat['avg']),
        "obp": float(stat['obp']),
        "slg": float(stat['slg']),
        "ops": float(stat['ops']),
        "hr": int(stat['homeRuns']),
        "rbi": int(stat['rbi']),
        "walks": int(stat['baseOnBalls']),
        "strikeouts": int(stat['strikeOuts']),
        "at_bats": int(stat['atBats']),
        "hits": int(stat['hits']),
        "games": int(stat['gamesPlayed'])
    }

# get_batter_stats()
@tool
def get_batter_stats(player_name: str) -> dict | str:
    """
    Retrieves current season batting stats for a player.
    Use this when the user asks about a batter's overall season performance,
    stats, or how a player is doing this year. Also use this for start/sit
    decisions for position players and batters.

    Args:
        player_name: The full or partial name of the batter. Example: 'Ohtani' or 'Shohei Ohtani'.

    Returns:
        A dictionary with the player's current season stats,
        or a string message explaining why data is not available.
    """
    player_id = get_player_id(player_name)

    if player_id is None:
        return f"No player found matching '{player_name}'. Check the spelling and try again."

    if isinstance(player_id, list):
        names = ", ".join(player_id)
        return f"Multiple players found matching '{player_name}': {names}. Please be more specific."

    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&season=2026&group=hitting"
    data = call_mlb_api(url)

    if data is None or not data['stats'][0]['splits']:
        return f"No stats found for '{player_name}' this season."

    stat = data['stats'][0]['splits'][0]['stat']

    return {
        "player": player_name,
        "season": "2026",
        "avg": float(stat['avg']),
        "obp": float(stat['obp']),
        "slg": float(stat['slg']),
        "ops": float(stat['ops']),
        "hr": int(stat['homeRuns']),
        "rbi": int(stat['rbi']),
        "sb": int(stat['stolenBases']),
        "bb": int(stat['baseOnBalls']),
        "so": int(stat['strikeOuts']),
        "games": int(stat['gamesPlayed']),
        "pa": int(stat['plateAppearances'])
    }

# ============================================================
# PITCHING TOOLS
# ============================================================

# get_pitcher_stats()
@tool
def get_pitcher_stats(player_name: str) -> dict | str:
    """
    Retrieves current season pitching stats for a pitcher.
    Use this when the user asks about a pitcher's overall season performance,
    ERA, strikeouts, or how a pitcher is doing this year.

    Args:
        player_name: The full or partial name of the pitcher. Example: 'deGrom' or 'Jacob deGrom'.

    Returns:
        A dictionary with the pitcher's current season stats,
        or a string message explaining why data is not available.
    """
    player_id = get_pitcher_id(player_name)

    if player_id is None:
        return f"No pitcher found matching '{player_name}'. Check the spelling and try again."

    if isinstance(player_id, list):
        names = ", ".join(player_id)
        return f"Multiple pitchers found matching '{player_name}': {names}. Please be more specific."

    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&season=2026&group=pitching"
    data = call_mlb_api(url)

    if data is None or not data['stats'][0]['splits']:
        return f"No stats found for '{player_name}' this season."

    stat = data['stats'][0]['splits'][0]['stat']

    return {
        "player": player_name,
        "season": "2026",
        "era": float(stat['era']),
        "whip": float(stat['whip']),
        "wins": int(stat['wins']),
        "losses": int(stat['losses']),
        "strikeouts": int(stat['strikeOuts']),
        "walks": int(stat['baseOnBalls']),
        "innings_pitched": float(stat['inningsPitched']),
        "hits_allowed": int(stat['hits']),
        "home_runs_allowed": int(stat['homeRuns']),
        "games": int(stat['gamesPlayed']),
        "games_started": int(stat['gamesStarted'])
    }

# ============================================================
# MATCHUP TOOLS
# ============================================================