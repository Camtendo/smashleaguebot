import React, { useState, useEffect } from 'react'

import axios from 'axios'
import { LeagueContext } from "../contexts/League"
import ToolTip from "../Components/ToolTip"
import './MatchEditor.css'

function MatchEditor({ match, allPlayers }) {

    const [ leagueState, dispatch ] = React.useContext(LeagueContext)
    const [ reload, setReload ] = useState(false)

    useEffect(() => {
      const fetchData = async () => {
        setReload(false)
      }

      fetchData().catch(console.error);
    }, [leagueState.checkForCommandsToRun, reload]);

    const clearScore = () => {
      const updateServer = async () => {
        await axios.post(`clear-score`, { leagueName: leagueState.selectedLeague, matchId: match.id });
        // TODO Probably wanna grab the match from the db again
        match.winner_id = null
        match.sets = 0
        match.date_played = null
        dispatch({ type: "need_to_check_for_commands", checkForCommandsToRun:true})
      }
      updateServer().catch(console.error);
    }

    const setWinner = (winnerId, loserId) => {
      const updateServer = async () => {
        await axios.post(`set-score`, { leagueName: leagueState.selectedLeague, matchId: match.id, winnerId, sets: match.sets_needed });
        // TODO Probably wanna grab the match from the db again
        match.winner_id = winnerId
        match.sets = match.sets_needed
        dispatch({ type: "need_to_check_for_commands", checkForCommandsToRun:true})
        setReload(true)
      }
      updateServer().catch(console.error);
    }

    const updateLoserScore = (winnerId, loserId, loserSets) => {
      var loserSetsInt = parseInt(loserSets)
      if (loserSetsInt < 0 || loserSetsInt >= match.sets_needed) return

      const updateServer = async () => {
        await axios.post(`set-score`, { leagueName: leagueState.selectedLeague, matchId: match.id, winnerId, sets: match.sets_needed + loserSetsInt });
        // TODO Probably wanna grab the match from the db again
        match.sets = match.sets_needed + loserSetsInt
        dispatch({ type: "need_to_check_for_commands", checkForCommandsToRun:true})
        setReload(true)
      }
      updateServer().catch(console.error);
    }

    const setMatchForfeit = () => {
      const updateServer = async () => {
        await axios.post(`set-forfeit`, { leagueName: leagueState.selectedLeague, matchId: match.id, forfeit: !match.forfeit });
        // TODO Probably wanna grab the match from the db again
        match.forfeit = !match.forfeit
        dispatch({ type: "need_to_check_for_commands", checkForCommandsToRun:true})
        setReload(true)
      }
      updateServer().catch(console.error);
    }

    let p1_score = '';
    let p2_score = '';
    if (match.player_1_id === match.winner_id && match.winner_id !== null) {
        p1_score = ''+match.sets_needed
        p2_score = ''+(match.sets - match.sets_needed)
    } else if (match.player_2_id === match.winner_id && match.winner_id !== null) {
        p1_score = ''+(match.sets - match.sets_needed)
        p2_score = ''+match.sets_needed
    }

    const p_name = (p_id) => {
        if (p_id === null) {
            return "Bye"
        }
        for (var p of allPlayers) {
            if (p.slack_id === p_id) return p.name
        }
        return p_id
    }

    return (
        <div className="match-item">
            <div className="match-group">{match.grouping}</div>
            <table className="match-editor-table">
              <tr>
                <th>Player</th>
                <th>Score</th>
                <th>Winner</th>
              </tr>
              <tr>
                <td>{p_name(match.player_1_id)}</td>
                <td><input className="score-field" disabled={match.winner_id !== match.player_2_id} type="number" value={p1_score} onChange={(e) => updateLoserScore(match.player_2_id, match.player_1_id, e.target.value)} /></td>
                <td><input className="winner-radio" type="radio" name={match.id+"_winner"} checked={match.winner_id === match.player_1_id} onChange={(e) => setWinner(match.player_1_id, match.player_2_id)} /></td>
              </tr>
              <tr>
                <td>{p_name(match.player_2_id)}</td>
                <td><input className="score-field" disabled={match.winner_id !== match.player_1_id} type="number" value={p2_score} onChange={(e) => updateLoserScore(match.player_1_id, match.player_2_id, e.target.value)} /></td>
                <td><input className="winner-radio" type="radio" name={match.id+"_winner"} checked={match.winner_id === match.player_2_id} onChange={(e) => setWinner(match.player_2_id, match.player_1_id)} /></td>
              </tr>
            </table>

            <div className="edit-match-controls">
              <div>
                <span style={{ marginRight: 5 }}>Was forfeit? <input type="checkbox" checked={match.forfeit} onChange={setMatchForfeit}/></span>
                <ToolTip size={14} width={240} text={"Mark the match as a forfeit. This allows you to set a winner and score for group rank and tie breaker purposes, but the match won't be included in historical and elo data."} />
              </div>
              { match.winner_id !== null &&
                <button onClick={clearScore}>Clear Score</button>
              }
            </div>

        </div>
    );
}

export default MatchEditor;