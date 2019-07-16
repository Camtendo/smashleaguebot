from slackclient import SlackClient
import bot_config
import db
import collections
from match_making import gather_scores, get_player_name
import time
from websocket import WebSocketConnectionClosedException
from multiprocessing import Process

import logging, sys

class SmashBot():
    def __init__(self):
        self.slack_client = SlackClient(bot_config.get_slack_api_key())
        self.logger = logging.getLogger('smashbot')

        hdlr = logging.FileHandler(bot_config.get_log_path())
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.DEBUG)

        self.logger.debug('booting up smashbot file')

    def keepalive(self):
        while True:
            time.sleep(3)
            try:
                self.slack_client.server.ping()
            except WebSocketConnectionClosedException as e:
                self.logger.debug('Keep alive web socket exception.')
                self.slack_client.rtm_connect()

    def print_help(self, channel):
        message = 'I support the following:'
        message = message + '\n`@sul me over @them 2-2` or `@sul @them over me 2-1` - report a score'
        message = message + '\n`@sul group a` - see the current rankings of a group'
        message = message + '\n`@sul leaderboard` - see the leaderboard, sorted by winrate'
        message = message + '\n`@sul loserboard` - see the loserboard, sorted by winrate'
        self.slack_client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)

    def get_leaderboard(self, reverse_order=True):
        matches = db.get_matches()
        players = db.get_players()

        player_dict = dict()

        for player in players:
            player_dict[player.slack_id] = {
                'games_won': 0,
                'games_total': 0,
                'name': player.name
            }
        
        for match in matches:
            games_played = match.sets

            player_1 = player_dict[match.player_1_id]
            player_2 = player_dict[match.player_2_id]

            player_dict[match.player_1_id]['games_total'] = player_1['games_total'] + games_played
            player_dict[match.player_2_id]['games_total'] = player_2['games_total'] + games_played

            if match.player_1_id == match.winner_id:
                player_dict[match.player_1_id]['games_won'] = player_1['games_won'] + 2

                if games_played == 3:
                    player_dict[match.player_2_id]['games_won'] = player_2['games_won'] + 1

            elif match.player_2_id == match.winner_id:
                player_dict[match.player_2_id]['games_won'] = player_2['games_won'] + 2
                
                if games_played == 3:
                    player_dict[match.player_1_id]['games_won'] = player_1['games_won'] + 1
                
        
        winrate_dict = dict()
        for player_id, player in player_dict.items():
            winrate_dict[player['name']] = {
                'games_won': player['games_won'],
                'games_lost': player['games_total'] - player['games_won'],
                'winrate': round((player['games_won'] / player['games_total']) * 100, 2)
            }

        sorted_winrates = collections.OrderedDict(sorted(winrate_dict.items(), key=lambda x: x[1]['winrate'], reverse=reverse_order))

        return sorted_winrates
        
    def print_leaderboard(self, channel):
        sorted_winrates = self.get_leaderboard()

        message = ""
        for player_name in list(sorted_winrates)[:10]:
            player_object = sorted_winrates[player_name]
            message = message + f"\n {player_name}: {player_object['winrate']}% ({player_object['games_won']}-{player_object['games_lost']})"
        
        self.slack_client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)

    def print_loserboard(self, channel):
        sorted_winrates = self.get_leaderboard(False)

        message = ""
        for player_name in list(sorted_winrates)[:10]:
            player_object = sorted_winrates[player_name]
            message = message + f"\n {player_name}: {player_object['winrate']}% ({player_object['games_won']}-{player_object['games_lost']})"
        
        self.slack_client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)

    def print_group(self, channel, group):
        try:
            season = db.get_current_season()
            all_matches = db.get_matches_for_season(season)
            all_players = db.get_players()
            group_matches = [m for m in all_matches if m.grouping.lower() == group.lower()]

            if not len(group_matches):
                raise Exception('Not a match')

            players = gather_scores(group_matches)
            message = 'Group ' + group.upper() + ':'

            for p in players:
                message += '\n' + get_player_name(all_players, p['player_id']) + ' ' + str(p['m_w']) + '-' + str(p['m_l'])
                message += ' ('+str(p['s_w'])+'-'+str(p['s_l'])+')'

            self.slack_client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)
        except Exception as e:
            self.logger.debug(e)
            self.slack_client.api_call("chat.postMessage", channel=channel, text="Not a group (or I messed up).", as_user=True)

    def parse_first_slack_id(self, message):
        return message[message.index('<@') + 2 : message.index('>')].upper()
    
    def parse_second_slack_id(self, message):
        message = message[message.index('>') + 1:]
        return self.parse_first_slack_id(message)
    
    def parse_score(self, message):
        dash_index = message.index('-')
        score_substring = message[dash_index - 1 : dash_index + 2]

        if score_substring != "2-0" and score_substring != "2-1":
            raise Exception("Malformed score")

        score_1 = int(score_substring[0])
        score_2 = int(score_substring[2])

        return score_1, score_2

    def parse_message(self, command, poster):
        isAdmin = poster == bot_config.get_commissioner_slack_id()

        if isAdmin and command.startswith('<@'):
            winner = self.parse_first_slack_id(command)
            loser = self.parse_second_slack_id(command)
        elif command.startswith('me over '):
            winner = poster
            loser = self.parse_first_slack_id(command)
        elif command.startswith('<@') and command.index('over me') > 0:
            winner = self.parse_first_slack_id(command)
            loser = poster
        else:
            self.logger.debug('Bad message format')
            return None

        if winner == loser:
            self.logger.debug('Cant player yourself')
            return None

        try:
            score_1, score_2 = self.parse_score(command)
        except Exception as e:
            self.logger.debug('Malformed score', e)
            return None

        return {
            'winner_id': winner,
            'loser_id': loser,
            'score_total': (score_1 + score_2)
        }

    def enter_score(self, winner_id, loser_id, score_total, channel, timestamp):
        try:
            if not db.update_match_by_id(winner_id, loser_id, score_total):
                self.slack_client.api_call("chat.postMessage", channel=channel, text='Not a match I have (or I messed up).', as_user=True)
                self.slack_client.api_call("reactions.add", name="x", channel=channel, timestamp=timestamp)
                return

            self.slack_client.api_call("chat.postMessage", channel=bot_config.get_commissioner_slack_id(), text='Entered into db', as_user=True)
            self.slack_client.api_call("reactions.add", name="white_check_mark", channel=channel, timestamp=timestamp)

        except Exception as e:
            self.slack_client.api_call("chat.postMessage", channel=bot_config.get_commissioner_slack_id(), text='Failed to enter into db', as_user=True)
            self.slack_client.api_call("reactions.add", name="x", channel=channel, timestamp=timestamp)

            self.logger.error(e)

    def filter_invalid_messages(self, message_list):
        valid_messages = []

        for message_object in message_list:
            if message_object is None:
                continue
            
            if 'text' not in message_object or 'channel' not in message_object or 'user' not in message_object or 'ts' not in message_object:
                continue

            if 'bot_id' in message_object:
                continue

            message_text = message_object['text']
            if message_object['channel'][:1] == 'D':
                if message_text.startswith('<@' + bot_config.get_bot_slack_user_id() + '>'):
                    message_text = message_text[message_text.index(">") + 1:].strip()

                message_object['text'] = message_text
                valid_messages.append(message_object)
                continue

            if message_object['channel'] == bot_config.get_channel_slack_id() and message_text.startswith('<@' + bot_config.get_bot_slack_user_id() + '>'):
                message_text = message_text[message_text.index(">") + 1:].strip()

                message_object['text'] = message_text
                valid_messages.append(message_object)
                continue

        return valid_messages
    
    def handle_message(self, message_object):
        command = message_object["text"]
        channel = message_object["channel"]
        user_id = message_object["user"]
        timestamp = message_object["ts"]

        if command == 'leaderboard':
            self.print_leaderboard(channel)
        elif command == 'loserboard' or command == 'troy':
            self.print_loserboard(channel)
        elif command == 'help':
            self.print_help(channel)
        elif command.startswith('group'):
            self.print_group(channel, command[6])
        else:
            result = None
            try:
                result = self.parse_message(command, user_id)
            except Exception as e:
                self.logger.debug(e)

            if result is None:
                format_msg = "Didn't catch that. The format is `@sul me over @them 2-1` or `@sul @them over me 2-1`."
                self.slack_client.api_call("chat.postMessage", channel=channel, text=format_msg, as_user=True)
            elif result is not None and channel[:1] == 'D':
                format_msg = "Nice try, you have to put this in the main channel"
                self.slack_client.api_call('chat.postMessage', channel=channel, text=format_msg, as_user=True)
            elif result is not None and channel == bot_config.get_channel_slack_id():
                self.enter_score(result['winner_id'], result['loser_id'], result['score_total'], channel, timestamp)

                player = db.get_player_by_id(result['winner_id'])
                self.print_group(channel, player.grouping)

        return None
    
    def start_bot(self):
        p = Process(target=self.keepalive)
        p.start()

        if self.slack_client.rtm_connect():
            print("StarterBot connected and running!")

            while True:
                try:
                    message_list = self.slack_client.rtm_read()
                    message_list = self.filter_invalid_messages(message_list)

                    for message in message_list:
                        try:
                            self.handle_message(message)
                        except Exception as e:
                            self.logger.debug(e)
                            self.slack_client.api_call("reactions.add", name="x", channel=message["channel"], timestamp=message["ts"])

                    time.sleep(1)
                except Exception as e:
                    self.logger.debug('Main while loop web socket exception.', e)
                    self.slack_client.rtm_connect()
        else:
            print("Connection failed. Invalid Slack token or bot ID?")

if __name__ == "__main__":
    SmashBot().start_bot()