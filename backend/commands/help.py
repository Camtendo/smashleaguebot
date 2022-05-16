from backend import slack_util, configs


def handles_message(lctx, command_object):
    if command_object.text.upper().startswith('HELP'):
        return True
    return False


def handle_message(lctx, command_object):
    if command_object.is_dm():
        slack_util.post_message(lctx, dm_help(lctx), command_object.channel)
    else:
        slack_util.post_message(lctx, channel_help(lctx), command_object.channel)


def channel_help(lctx):
    bot_name = lctx.configs[configs.BOT_NAME]
    example_score = lctx.configs[configs.SCORE_EXAMPLE]
    message = 'In the channel, I support the following:'
    message = message + '\n`{} me over @them {}` or `{} @them over me {}` - report a score'.format(bot_name, example_score, bot_name, example_score)
    message = message + '\n`{} group [a, b, c, etc]` - see the current rankings of a group'.format(bot_name)
    message = message + '\n`{} leaderboard [matches, sets, winrate]` - see the leaderboard, sorted by matches, sets, or winrate'.format(bot_name)
    # message = message + '\n`{} loserboard` - see the loserboard, sorted by winrate'.format(bot_name)
    # message = message + '\n`{} matches for week` - see all matches occuring this week in all groups'.format(bot_name)
    return message


def dm_help(lctx):
    bot_name = lctx.configs[configs.BOT_NAME]
    example_score = lctx.configs[configs.SCORE_EXAMPLE]
    message = 'In DMs, I support the following:'
    message = message + '\n`group [a, b, c, etc]` - see the current rankings of a group'
    message = message + '\n`leaderboard [matches, sets, winrate]` - see the leaderboard, sorted by matches, sets, or winrate'
    message = message + '\n`my total stats` - see your total win/loss record for the league'
    # message = message + '\n`who do i play` - see who you play this week (only in dms)'
    # message = message + '\n`matches for week` - see all matches occurring this week in all groups'
    return message
