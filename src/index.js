import React from 'react';
import ReactDOM from 'react-dom';
import { Route, Link, BrowserRouter as Router } from 'react-router-dom'

import './index.css';
import App from './Reminders/App';
import Playerboard from './Playerboard/Playerboard';
import NotFound from './NotFound/NotFound'

import * as serviceWorker from './serviceWorker';
import 'bootstrap/dist/css/bootstrap.css';

const routing = (
    <Router>
      <div>
        <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
          <ul className="navbar-nav">
            <li className="nav-item">
              <Link className="nav-link" to="/">Reminders</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/playerboard">Playerboard</Link>
            </li>
          </ul>
        </nav>
        <Route exact path="/" component={App} />
        <Route path="/playerboard" component={Playerboard} />
        { /* <Route component={NotFound} /> */ }
      </div>
    </Router>
  )

ReactDOM.render(routing, document.getElementById('root'));

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();
