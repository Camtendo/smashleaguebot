import re

from backend import slack_util, configs, db
from backend.commands import group

BLOCK_NEW_SCORES_MSG = "Sorry, not accepting any scores at this time."
PLAYED_YOURSELF_MSG = "You can't play against yourself."
NO_MATCH_MSG = "I couldn't find a match between you two."
WORKED_REACTION = "white_check_mark"
NOT_WORKED_REACTION = "x"

TAG_RE = re.compile(r'<@([^>|\s]+)(?:\|[^>]*)?>')


def split_sides(text):
    idx = text.lower().find(' over ')
    if idx == -1:
        return None
    return text[:idx], text[idx + len(' over '):]


def _tokens(side_text):
    spaced = TAG_RE.sub(lambda m: ' <@{}> '.format(m.group(1)), side_text)
    return [t for t in re.split(r'[\s,&]+', spaced) if t]


def mentions_me(side_text):
    return any(token.lower() == 'me' for token in _tokens(side_text))


def side_ids(side_text, sender):
    ids = []
    for token in _tokens(side_text):
        tag = TAG_RE.fullmatch(token)
        if tag:
            uid = tag.group(1)
        elif token.lower() == 'me':
            uid = sender
        else:
            continue
        if uid not in ids:
            ids.append(uid)
    return ids


def parse_sides(text, sender):
    sides = split_sides(text)
    if sides is None:
        return None
    winners, losers = side_ids(sides[0], sender), side_ids(sides[1], sender)
    if not winners or not losers:
        return None
    return winners, losers


def handles_message(lctx, command_object):
    is_admin = command_object.user == lctx.configs[configs.COMMISSIONER_SLACK_ID] and command_object.is_dm()
    if not is_admin and command_object.channel != lctx.configs[configs.COMPETITION_CHANNEL_SLACK_ID]:
        return False
    text = command_object.text
    if not (re.match(r'(?i)me\b', text) or text.startswith('<@')):
        return False
    sides = split_sides(text)
    if sides is None or parse_sides(text, command_object.user) is None:
        return False
    left_me, right_me = mentions_me(sides[0]), mentions_me(sides[1])
    if is_admin:
        return not left_me and not right_me
    return left_me != right_me


def get_format_message(lctx):
    example_score = lctx.configs[configs.SCORE_EXAMPLE]
    bot_name = lctx.configs[configs.BOT_NAME]
    return "Didn't catch that. The format is `{} me over @them {}` or `{} @them over me {}`".format(bot_name, example_score, bot_name, example_score)


def handle_message(lctx, command_object):
    if lctx.configs[configs.BLOCK_NEW_SCORES] == 'TRUE':
        slack_util.post_message(lctx, BLOCK_NEW_SCORES_MSG, command_object.channel)
        return

    sides = parse_sides(command_object.text, command_object.user)
    if sides is None or len(sides[0]) != 1 or len(sides[1]) != 1:
        slack_util.post_message(lctx, get_format_message(lctx), command_object.channel)
        return
    users = {'winner_id': sides[0][0], 'loser_id': sides[1][0]}

    if users['winner_id'] == users['loser_id']:
        slack_util.post_message(lctx, PLAYED_YOURSELF_MSG, command_object.channel)
        return

    matches = db.get_matches_for_season(lctx.league_name, db.get_current_season(lctx.league_name))
    tmp = [x for x in matches if x.player_1_id == users['winner_id'] and x.player_2_id == users['loser_id'] or
           x.player_2_id == users['winner_id'] and x.player_1_id == users['loser_id']]
    if len(tmp) == 0:
        slack_util.post_message(lctx, NO_MATCH_MSG, command_object.channel)
        return

    match = tmp[0]
    winner_score = 0
    loser_score = 0
    tie_score = 0
    if match.play_all_sets:  # Total score needs to match the sets_needed value
        try:
            winner_score, loser_score, tie_score = parse_score(command_object.text)
            if winner_score + loser_score + tie_score != match.sets_needed:
                raise Exception("Incorrect points")
        except Exception as e:
            slack_util.post_message(lctx, get_format_message(lctx), command_object.channel)
            return
    elif match.sets_needed > 1:
        try:
            winner_score, loser_score, tie_score = parse_score(command_object.text)
            if tie_score > 0:
                raise Exception("Incorrect points")
            if winner_score != match.sets_needed and loser_score != match.sets_needed:
                raise Exception("Incorrect points")
            if winner_score + loser_score < match.sets_needed or winner_score + loser_score >= match.sets_needed*2:
                raise Exception("Incorrect points")
        except Exception as e:
            slack_util.post_message(lctx, get_format_message(lctx), command_object.channel)
            return
    else:
        winner_score = 1

    is_admin = command_object.user == lctx.configs[configs.COMMISSIONER_SLACK_ID] and command_object.is_dm()
    try:
        db.update_match_by_id(lctx.league_name, users['winner_id'], users['loser_id'], winner_score, loser_score, tie_score)
        slack_util.add_reaction(lctx, command_object.channel, command_object.timestamp, WORKED_REACTION)

    except Exception as e:
        slack_util.post_message(lctx, 'Failed to enter into db', lctx.configs[configs.COMMISSIONER_SLACK_ID])
        slack_util.add_reaction(lctx, command_object.channel, command_object.timestamp, NOT_WORKED_REACTION)
        print(e)
        return

    if not is_admin:
        if lctx.configs[configs.MESSAGE_COMMISSIONER_ON_SUCCESS] == 'TRUE':
            slack_util.post_message(lctx, 'Entered into db', lctx.configs[configs.COMMISSIONER_SLACK_ID])
        player = db.get_player_by_id(lctx.league_name, users['winner_id'])
        group_msg = group.build_message_for_group(lctx, player.grouping)
        slack_util.post_message(lctx, group_msg, command_object.channel)


def parse_score(message):
    dash_index = message.index('-')
    score_substring = message[dash_index - 1: dash_index + 2]

    winner_score = int(score_substring[0])
    loser_score = int(score_substring[2])
    tie_score = 0

    after_dash = message[dash_index+1:]
    if '-' in after_dash:
        tie_score = int(after_dash[after_dash.index('-')+1:after_dash.index('-')+2])

    return winner_score, loser_score, tie_score
