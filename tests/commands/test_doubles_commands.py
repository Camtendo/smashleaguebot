import datetime
from unittest import TestCase
from unittest.mock import patch

from tests import test_league_setup
from tests import doubles_fixture
from backend import db, slack_util, utility
from backend.commands import group, group_analysis
from backend.commands.command_message import CommandMessage
from backend.league_context import LeagueContext

league_name = 'unittest'


class Test(TestCase):
    def setUp(self):
        test_league_setup.teardown_test_league()
        test_league_setup.create_test_league()
        self.t = doubles_fixture.make_doubles_league(season_matches=False)
        week = datetime.date(2022, 1, 3)
        db.add_match_by_ids(league_name, self.t['AB'], self.t['CD'], week, 'A', 1, 3)
        db.add_match_by_ids(league_name, self.t['EF'], self.t['GH'], week, 'B', 1, 3)
        db.update_match_by_participants(league_name, self.t['AB'], self.t['CD'], 3, 1, 0)
        self.lctx = LeagueContext.load_from_db(league_name)

    def tearDown(self):
        test_league_setup.teardown_test_league()

    def test_group_message_shows_team_names(self):
        msg = group.build_message_for_group(self.lctx, 'A')
        self.assertEqual('Group A:\nBob-omb Squad (Alice & Bob) 1-0 (3-1)\nCarol & Dan 0-1 (1-3)', msg)

    def test_markup_has_doubles_standings(self):
        markup = utility.print_season_markup(self.lctx)
        self.assertIn('|Bob-omb Squad (Alice & Bob) 1-0|', markup)  # group B is a 0-0 tie; tie_breaker orders it randomly
        self.assertNotIn('|Bye', markup)
        self.assertIn('Bob-omb Squad (Alice & Bob) - 3<br>Carol & Dan - 1', markup)

    def test_analyze_group_uses_team_names(self):
        # The analyzer expects a real-size group (the singles golden uses 4), so put all 4 teams in a round robin in A.
        db.clear_matches_for_season(league_name, 1)
        ids = [self.t[k] for k in ('AB', 'CD', 'EF', 'GH')]
        db.update_team_grouping_and_orders(league_name, ids, 'A')
        for i in range(4):
            for j in range(i + 1, 4):
                db.add_match_by_ids(league_name, ids[i], ids[j], datetime.date(2022, 1, 3), 'A', 1, 3)
        db.update_match_by_participants(league_name, ids[0], ids[1], 3, 0, 0)
        with patch.object(slack_util, 'post_message') as mock_post:
            group_analysis.handle_message(self.lctx, CommandMessage('analyze group A', 'comp_channel', 'uA', '1'))
        text = mock_post.call_args.args[1]
        self.assertNotIn('Bye', text)
        self.assertTrue(any(name in text for name in ('Bob-omb Squad (Alice & Bob)', 'Carol & Dan', 'Erin & Frank', 'Gina & Hank')), text)
