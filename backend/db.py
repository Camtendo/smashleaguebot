import sqlite3
import os
import datetime

LATEST_VERSION = 1

_commands_to_run = {}


def get_commands_to_run(league_name):
    if league_name not in _commands_to_run:
        return []
    return _commands_to_run[league_name]


def add_command_to_run(league_name, command):
    if league_name not in _commands_to_run:
        _commands_to_run[league_name] = []
    _commands_to_run[league_name].append(command)


def clear_commands_to_run(league_name):
    _commands_to_run[league_name] = []


def path(league_name):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../{}_league.sqlite".format(league_name)))


def get_connection(league_name):
    return sqlite3.connect(path(league_name), detect_types=sqlite3.PARSE_DECLTYPES)


def initialize(league_name):
    if os.path.exists(path(league_name)):
        return

    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute('CREATE TABLE player ('
              'slack_id TEXT PRIMARY KEY, '
              'name TEXT, '
              'grouping TEXT, '
              'active INT, '
              'order_idx INT DEFAULT 0)')
    c.execute('CREATE TABLE match ('
              'player_1 TEXT, '
              'player_2 TEXT, '
              'winner TEXT, '
              'week DATE, '
              'grouping TEXT, '
              'season INT, '
              'sets INT, '
              'sets_needed INT, '
              'date_played DATE, '
              'message_sent INT DEFAULT 0, '
              'FOREIGN KEY (player_1) REFERENCES player, '
              'FOREIGN KEY (player_2) REFERENCES player, '
              'FOREIGN KEY (winner) REFERENCES player)')
    c.execute('CREATE TABLE config ('
              'name TEXT PRIMARY KEY, '
              'value TEXT)')

    conn.commit()
    conn.close()
    set_config(league_name, 'LEAGUE_VERSION', str(LATEST_VERSION))


def set_config(league_name, name, value):
    command = "INSERT INTO config VALUES ('{}', '{}') " \
              "ON CONFLICT(name) DO UPDATE SET value='{}' where name='{}'".format(name, value, value, name)
    add_command_to_run(league_name, command)

    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()


def get_config(league_name, name):
    initialize(league_name)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE name = '{}'".format(name))
    rows = c.fetchall()
    conn.close()
    if rows:
        return rows[0][0]
    return None


def add_player(league_name, slack_id, name, grouping):
    command = "INSERT INTO player (slack_id, name, grouping, active) VALUES ('{}', '{}', '{}', 1)".format(slack_id, name.replace("'","''"), grouping)
    add_command_to_run(league_name, command)

    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()


class Player:
    def __init__(self, slack_id, name, grouping, active, order_idx):
        self.slack_id = slack_id
        self.name = name
        self.grouping = grouping
        self.active = active
        self.order_idx = order_idx

    @classmethod
    def from_db(cls, row):
        return Player(row[0], row[1], row[2], row[3], row[4])

    def __str__(self):
        return self.name + ' ' + self.slack_id + ' ' + self.grouping + ' ' + str(self.active)

    def __repr__(self):
        return self.name + ' ' + self.slack_id + ' ' + self.grouping + ' ' + str(self.active)

    def __eq__(self, other):
        if other is None:
            return False
        return self.slack_id == other.slack_id and self.name == other.name


def get_players(league_name):
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute('SELECT * FROM player')
    rows = c.fetchall()
    conn.close()
    return [Player.from_db(p) for p in rows]


def get_active_players(league_name):
    return [p for p in get_players(league_name) if p.active]


def get_player_by_name(league_name, name):
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute("SELECT * FROM player WHERE name = '{}'".format(name))
    row = c.fetchone()
    conn.close()
    if row is None or len(row) == 0:
        print('Could not find player with name:', name)
        return None
    return Player.from_db(row)


def get_player_by_id(league_name, id):
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute("SELECT * FROM player WHERE slack_id = '{}'".format(id))
    row = c.fetchone()
    conn.close()
    if row is None or len(row) == 0:
        print('Could not find player with id:', id)
        return None
    return Player.from_db(row)


def update_grouping(league_name, slack_id, grouping):
    command = "UPDATE player SET grouping='{}' WHERE slack_id = '{}'".format(grouping, slack_id)
    add_command_to_run(league_name, command)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()


def updating_grouping_and_orders(league_name, slack_ids, grouping):
    conn = get_connection(league_name)
    c = conn.cursor()

    for idx, slack_id in enumerate(slack_ids):
        command = "UPDATE player SET grouping='{}', order_idx={}, active=1 WHERE slack_id = '{}'".format(grouping, idx, slack_id)
        add_command_to_run(league_name, command)
        c.execute(command)
    conn.commit()
    conn.close()


def update_player_order_idx(league_name, slack_id, order_idx):
    command = "UPDATE player set order_idx={} WHERE slack_id = '{}'".format(order_idx, slack_id)
    add_command_to_run(league_name, command)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()


def set_active(league_name, slack_id, active):
    active_int = 1 if active else 0
    command = "UPDATE player SET active={} WHERE slack_id = '{}'".format(active_int, slack_id)
    add_command_to_run(league_name, command)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()


def add_match(league_name, player_1, player_2, week_date, grouping, season, sets_needed):

    if player_1 is None or player_2 is None:
        p_id = player_1.slack_id if player_1 is not None else player_2.slack_id
        command = "INSERT INTO match (player_1, week, grouping, season, sets, sets_needed) VALUES ('{}', '{}', '{}', {}, 0, {})".format(p_id, str(week_date), grouping, season, sets_needed)
    else:
        command = "INSERT INTO match (player_1, player_2, week, grouping, season, sets, sets_needed) VALUES ('{}', '{}', '{}', '{}', {}, 0, {})".format(player_1.slack_id, player_2.slack_id, str(week_date), grouping, season, sets_needed)

    add_command_to_run(league_name, command)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()


class Match:
    def __init__(self, id, p1_id, p2_id, winner_id, week, grouping, season, sets, sets_needed, date_played, message_sent):
        self.id = id
        self.player_1_id = p1_id
        self.player_2_id = p2_id
        self.winner_id = winner_id
        self.week = week
        self.grouping = grouping
        self.season = season
        self.sets = sets
        self.sets_needed = sets_needed
        self.date_played = date_played
        self.message_sent = message_sent

    @classmethod
    def from_db(cls, row):
        return Match(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10])

    @classmethod
    def from_dict(cls, d):
        return Match(d['id'], d['player_1_id'], d['player_2_id'], d['winner_id'], d['week'], d['grouping'], d['season'], d['sets'], d['sets_needed'])


def get_matches(league_name):
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute('SELECT rowid, * FROM match')
    rows = c.fetchall()
    conn.close()

    return [Match.from_db(m) for m in rows]


def get_matches_for_season(league_name, season):
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute('SELECT rowid, * FROM match WHERE season = {}'.format(season))
    rows = c.fetchall()
    conn.close()

    return [Match.from_db(m) for m in rows]


def clear_matches_for_season(league_name, season):
    command = 'DELETE FROM match WHERE season = {}'.format(season)
    add_command_to_run(league_name, command)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()


def get_matches_for_week(league_name, week):
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute("SELECT rowid, * FROM match WHERE week = '{}'".format(week))
    rows = c.fetchall()
    conn.close()

    return [Match.from_db(m) for m in rows]


def get_match_by_players(league_name, player_a, player_b):
    if player_a.slack_id == player_b.slack_id:
        return None
    season = get_current_season(league_name)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute("SELECT rowid, * FROM match WHERE season = {} and (player_1 = '{}' or player_2 = '{}') and (player_1 = '{}' or player_2 = '{}')"\
              .format(season, player_a.slack_id, player_a.slack_id, player_b.slack_id, player_b.slack_id))
    row = c.fetchone()
    conn.close()

    if row is None or len(row) == 0:
        print("No match for players:", player_a.name, player_b.name)
        return None
    return Match.from_db(row)


def update_match(league_name, winner_name, loser_name, sets):
    winner = get_player_by_name(league_name, winner_name)
    loser = get_player_by_name(league_name, loser_name)
    return _update_match(league_name, winner, loser, sets)


def update_match_by_id(league_name, winner_id, loser_id, sets):
    winner = get_player_by_id(league_name, winner_id)
    loser = get_player_by_id(league_name, loser_id)
    return _update_match(league_name, winner, loser, sets)


def _update_match(league_name, winner, loser, sets):
    if winner is None or loser is None:
        print('Could not update match')
        return False

    match = get_match_by_players(league_name, winner, loser)
    if match is None:
        print('Could not update match')
        return False

    if sets < match.sets_needed or sets > (match.sets_needed*2-1):
        print('Sets out of range, was {}, but must be between {} and {}'.format(sets, match.sets_needed, match.sets_needed*2-1))
        return False

    command = "UPDATE match SET winner='{}', sets={}, date_played='{}' WHERE player_1 = '{}' and player_2 = '{}' and season={}"\
              .format(winner.slack_id, sets, str(datetime.date.today()), match.player_1_id, match.player_2_id, match.season)
    add_command_to_run(league_name, command)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()
    return True


def admin_update_match(league_name, new_match):
    command = "UPDATE match SET " +\
              "player_1='{}', ".format(new_match.player_1_id) +\
              "player_2='{}', ".format(new_match.player_2_id) +\
              ("winner='{}', ".format(new_match.winner_id) if new_match.winner_id is not None else "winner=null, ") +\
              "week='{}', ".format(new_match.week) +\
              "grouping='{}', ".format(new_match.grouping) +\
              "sets={}, ".format(new_match.sets) +\
              "sets_needed={} ".format(new_match.sets_needed) +\
              "WHERE rowid={}".format(new_match.id)
    add_command_to_run(league_name, command)
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute(command)
    conn.commit()
    conn.close()
    return True


def get_current_season(league_name):
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute("SELECT MAX(season) FROM match")
    rows = c.fetchall()
    conn.close()
    current_season = rows[0][0]
    if current_season is None:
        return 0
    return current_season


def get_all_seasons(league_name):
    conn = get_connection(league_name)
    c = conn.cursor()
    c.execute("SELECT distinct season FROM match")
    rows = c.fetchall()
    conn.close()
    if rows is None or len(rows) == 0:
        return []
    seasons = [x[0] for x in rows]
    seasons.sort()
    return seasons
