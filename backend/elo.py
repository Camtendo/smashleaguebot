import math

def compute_all_elo_ratings(all_matches, all_players, base_elo=1500, k_factor = 32, group_step = 50):
    # Filter out matches with no winner and sort by date played (or week), also filter out forfeits
    sorted_matches = sorted([x for x in all_matches if x.winner_id and not x.forfeit],
                            key = lambda x: str(x.date_played if x.date_played else x.week) + str(x.week) )

    # Build a map of season -> set of group letters in that season
    distinct_seasons = sorted(list(set([m.season for m in sorted_matches if m.season is not None])))
    season_groups = {}
    for season in distinct_seasons:
        season_groups[season] = sorted(list(set([m.grouping.upper() for m in sorted_matches if m.season == season and m.grouping])))

    # Helper function for group bonus
    def group_bonus(group_letter, season):
        if not group_letter or not group_letter.isalpha() or len(group_letter) != 1:
            return 0
        
        groups = list(season_groups.get(season, []))
        if not groups:
            return 0
            
        group_char_codes = [ord(g) for g in groups]
        min_code = min(group_char_codes)
        max_code = max(group_char_codes)
        code = ord(group_letter.upper())
        
        if max_code == min_code:
            return 0
        
        norm = (max_code - code) / (max_code - min_code)
        return round(norm * group_step, 2)

    # Initialize ELOs
    elos = {}
    for player in all_players:
        # Find the first season a player appears in
        player_seasons = sorted(list(set([m.season for m in sorted_matches if m.player_1_id == player.slack_id or m.player_2_id == player.slack_id])))
        first_season = player_seasons[0] if player_seasons else None

        group_letter = None
        if first_season:
            group_letter = list(set([m.grouping for m in sorted_matches if (m.player_1_id == player.slack_id or m.player_2_id == player.slack_id) and m.season == first_season]))[0]
        else:
            group_letter = player.grouping
        elos[player.slack_id] = base_elo + group_bonus(group_letter, first_season or 1)

    # Go through each match and update ELOs
    for match in sorted_matches:
        p1 = match.player_1_id
        p2 = match.player_2_id
        if not p1 or not p2 or p1 not in elos or p2 not in elos:
            continue

        elo1 = elos[p1]
        elo2 = elos[p2]

        expected1 = 1 / (1 + math.pow(10, (elo2 - elo1) / 400))
        expected2 = 1 - expected1

        score1, score2 = 0.5, 0.5
        if match.winner_id == p1:
            score1, score2 = 1, 0
        elif match.winner_id == p2:
            score1, score2 = 0, 1

        # round to the nearest hundredth
        elos[p1] = round(elo1 + k_factor * (score1 - expected1), 2)
        elos[p2] = round(elo2 + k_factor * (score2 - expected2), 2)

    # Final rounding to nearest integer
    for player_id in elos:
        elos[player_id] = round(elos[player_id])
    return elos

