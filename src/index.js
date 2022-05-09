import React from 'react';
import ReactDOM from 'react-dom';
import { Route, Link, HashRouter as Router } from 'react-router-dom'

import './index.css';
import AdminConfig from './AdminConfig/AdminConfig';
import Configuration from './Configuration/Configuration';
import App from './Reminders/App';
import Playerboard from './Playerboard/Playerboard';
import Playerboard2 from './Playerboard2/Playerboard2';
import NotFound from './NotFound/NotFound'
import Matches from './Matches/Matches';
import LeagueSelector from './Components/LeagueSelector';

import * as serviceWorker from './serviceWorker';
import 'bootstrap/dist/css/bootstrap.css';
import { LeagueProvider } from "./contexts/League"

const routing = (
    <LeagueProvider>
    <Router>
      <div>
        <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
          <ul className="navbar-nav">
            <li className="nav-item">
              <Link className="nav-link" to="/admin">Admin</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/configuration">Configuration</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/matches">Matches</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/">Reminders</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/playerboard">Playerboard</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/playerboard2">Playerboard2</Link>
            </li>
            <li className="nav-item">
              <LeagueSelector />
            </li>
          </ul>
        </nav>

        <Route exact path="/" component={App} />
        <Route path="/playerboard" component={Playerboard} />
        <Route path="/playerboard2" component={Playerboard2} />
        <Route path="/configuration" component={Configuration} />
        <Route path="/admin" component={AdminConfig} />
        <Route path="/matches" component={Matches} />
        { /* <Route component={NotFound} /> */ }
      </div>
    </Router>
    </LeagueProvider>
  )

ReactDOM.render(routing, document.getElementById('root'));

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();
