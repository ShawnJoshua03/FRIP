<div align="center">

# FRIP: Fractional Rental Investment Platform

A full-stack web application where users pool money to collectively invest in rental properties and receive proportional returns.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-PyMongo-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![JavaScript](https://img.shields.io/badge/JavaScript-Vanilla-F7DF1E?logo=javascript&logoColor=black)](https://developer.mozilla.org/docs/Web/JavaScript)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.x-FF6384?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![Write-up](https://img.shields.io/badge/Write--up-read-14b8a6)](https://shawnjoshua03.github.io/stories/frip/)

<img src="https://shawnjoshua03.github.io/images/frip.jpg" alt="FRIP screenshot" width="800">

**[Write-up](https://shawnjoshua03.github.io/stories/frip/)** · **[Portfolio](https://shawnjoshua03.github.io/)**

</div>

> **Note:** The hosted demo is currently down (its API returns a server error). Please run the project locally using the [Quick Start](#quick-start) below.

## Tech Stack

| Layer      | Technology                            |
|------------|---------------------------------------|
| Backend    | Python 3.12, Flask 3.0               |
| Database   | MongoDB (PyMongo)                     |
| Auth       | Flask sessions + bcrypt               |
| Frontend   | Vanilla HTML, CSS, JavaScript         |
| Charts     | Chart.js 4.x (CDN)                   |
| Deployment | Vercel                                |

## Quick Start

### 1. Prerequisites

- Python 3.10+
- A MongoDB instance (local or Atlas)

### 2. Install dependencies

```bash
cd FRIP
pip install -r backend/requirements.txt
```

### 3. Configure environment

Edit `backend/.env`:

```env
MONGO_URI=mongodb://localhost:27017       # or your Atlas connection string
SECRET_KEY=some-random-secret-key-here
DB_NAME=frip_db
```

### 4. Run

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000). Three sample properties are seeded automatically on first launch.

## Project Structure

```
FRIP/
├── backend/
│   ├── app.py          # Flask app factory, page routes
│   ├── db.py           # MongoDB connection, indexes, seed data (properties and valuation history)
│   ├── risk.py         # Risk score and time-weighted return (Modified Dietz)
│   ├── routes.py       # All API endpoints (auth, properties, invest, portfolio, distributions, valuation)
│   ├── requirements.txt # Pinned Python dependencies
│   └── .env            # Environment variables (not committed)
├── frontend/
│   ├── template/
│   │   └── index.html  # Single-page shell with all page sections
│   └── static/
│       ├── style.css   # Complete hand-written CSS (dark fintech theme)
│       └── common.js   # Client-side SPA router, API calls, Chart.js rendering
├── run.py              # Development entry point
├── vercel.json         # Vercel deployment config
└── README.md
```

## API Endpoints

| Method | Route                          | Auth     | Description                     |
|--------|--------------------------------|----------|---------------------------------|
| POST   | `/auth/register`               | Public   | Register new user               |
| POST   | `/auth/login`                  | Public   | Log in                          |
| POST   | `/auth/logout`                 | Public   | Log out                         |
| GET    | `/auth/me`                     | Public   | Check current session           |
| GET    | `/properties`                  | Public   | List all properties             |
| GET    | `/properties/<id>`             | Public   | Property detail + investors     |
| POST   | `/investments`                 | Required | Invest in a property            |
| GET    | `/users/<id>/portfolio`        | Required | Dashboard portfolio data        |
| POST   | `/distributions/<property_id>` | Required | Trigger rental income payout    |
| POST   | `/properties/<id>/valuation`   | Required | Update a property's market value (body: `market_value`) |

## Features

- **Auth**: Register, login, logout with bcrypt-hashed passwords and Flask sessions
- **Property Browsing**: Card grid with funding progress, expected returns, monthly income
- **Investing**: Real-time ownership share recalculation across all investors
- **Dashboard**: Portfolio allocation doughnut chart, holdings summary, transaction history
- **Risk Score**: `GET /properties/<id>` returns a 0-100 score (Low < 30, Medium 30-55, High > 55) from a weighted average of five factors: volatility (25%), ownership concentration (20%), funding gap (20%), cap rate vs a 6% benchmark (20%) and depreciation (15%)
- **Time-Weighted Return**: the portfolio endpoint returns `twr_pct`, computed with the Modified Dietz method, alongside `roi_pct`
- **Valuations**: Update a property's market value; each update is recorded, and the valuation history and appreciation are returned with the property detail
- **Income Distribution**: Admin panel to trigger proportional payouts to all shareholders
- **Responsive**: Mobile-first CSS with dark navy/teal fintech aesthetic
- **SPA Routing**: Client-side `pushState` navigation with no full-page reloads

## Deployment to Vercel

1. Push to GitHub
2. Import the repo in [vercel.com](https://vercel.com)
3. Set environment variables in the Vercel dashboard:
   - `MONGO_URI` — your MongoDB Atlas connection string
   - `SECRET_KEY` — a random secret
   - `DB_NAME` — database name (e.g. `frip_db`)
4. Deploy

## Database Collections

**users**: `_id, name, email, password_hash, created_at`

**properties**: `_id, address, description, total_value, total_pooled_capital, expected_annual_return, rental_income, image_url, created_at, current_market_value`

**investments**: `_id, user_id, property_id, amount, ownership_share, timestamp`

**transactions**: `_id, user_id, property_id, type (invest|distribute), amount, timestamp`

**valuations**: `_id, property_id, market_value, date`
