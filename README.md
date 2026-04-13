# FRIP — Fractional Rental Investment Platform

A full-stack web application where users pool money to collectively invest in rental properties and receive proportional returns.

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
pip install -r requirements.txt
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
│   ├── db.py           # MongoDB connection, indexes, seed data
│   ├── routes.py       # All API endpoints (auth, properties, invest, portfolio, distributions)
│   └── .env            # Environment variables (not committed)
├── frontend/
│   ├── template/
│   │   └── index.html  # Single-page shell with all page sections
│   └── static/
│       ├── style.css   # Complete hand-written CSS (dark fintech theme)
│       └── common.js   # Client-side SPA router, API calls, Chart.js rendering
├── run.py              # Development entry point
├── vercel.json         # Vercel deployment config
├── requirements.txt    # Pinned Python dependencies
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

## Features

- **Auth**: Register, login, logout with bcrypt-hashed passwords and Flask sessions
- **Property Browsing**: Card grid with funding progress, expected returns, monthly income
- **Investing**: Real-time ownership share recalculation across all investors
- **Dashboard**: Portfolio allocation doughnut chart, holdings summary, transaction history
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

**properties**: `_id, address, description, total_value, total_pooled_capital, expected_annual_return, rental_income, image_url, created_at`

**investments**: `_id, user_id, property_id, amount, ownership_share, timestamp`

**transactions**: `_id, user_id, property_id, type (invest|distribute), amount, timestamp`