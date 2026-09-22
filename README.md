# Personal Finance Manager

A full-stack application for tracking personal income and expenses in EUR.

Built with FastAPI, PostgreSQL and vanilla JavaScript.

## Live Demo

[Open Personal Finance Manager](https://personal-finance-manager-vkfz.onrender.com)

Create an account to explore the app with sample transactions.
The first request may take about a minute while the free server wakes up.

Hosted on Render with PostgreSQL on Neon.

## Features

- Account registration and login with JWT authentication
- Password hashing with Argon2
- Create, view, edit and delete financial transactions
- User-specific data access and ownership checks
- Income, expense and net income summary
- Date range, transaction type and category filters
- Paginated transaction list
- Responsive web interface
- Interactive API documentation with Swagger UI

All amounts are recorded in EUR. Net income represents income minus
expenses for the selected period, not a bank account balance.

## Tech Stack

- Backend: Python, FastAPI, SQLAlchemy
- Database: PostgreSQL
- Migrations: Alembic
- Validation: Pydantic
- Authentication: PyJWT, pwdlib with Argon2
- Frontend: HTML, CSS, JavaScript

## Project Structure

```text
app/
├── config.py
├── database.py
├── security.py
├── models/
├── schemas/
├── services/
└── routers/
alembic/
static/
├── index.html
├── style.css
└── app.js
main.py
requirements.txt
.env.example
```

## Local Setup

Requirements: Python 3.10+ and a running PostgreSQL server.

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Create a PostgreSQL database

Using a PostgreSQL administrator account, create a database owned
by your application role:

```sql
CREATE DATABASE finance_manager OWNER your_db_user;
```

Replace `your_db_user` with an existing PostgreSQL role.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Update `DATABASE_URL` with your database credentials.

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into `JWT_SECRET` in `.env`.

Do not commit `.env` or real credentials.

### 4. Apply migrations

```bash
alembic upgrade head
```

### 5. Start the application

```bash
python -m uvicorn main:app --reload
```

- Application: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Create an account through the web interface to get started.

## API Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Register an account |
| POST | `/auth/login` | Obtain an access token |
| GET | `/auth/me` | Get the authenticated user |
| POST | `/transactions` | Create a transaction |
| GET | `/transactions` | List your transactions |
| GET | `/transactions/summary` | Get your financial summary |
| GET | `/transactions/{id}` | Get a transaction |
| PATCH | `/transactions/{id}` | Update a transaction |
| DELETE | `/transactions/{id}` | Delete a transaction |

Transaction endpoints require a Bearer token.

The list endpoint supports `type`, `category`, `date_from`,
`date_to`, `limit` and `offset`.

The summary endpoint supports `date_from` and `date_to`.
Date boundaries are inclusive.

## Implementation Details

- Monetary amounts use Python Decimal and PostgreSQL NUMERIC(12, 2).
- Amounts are positive; transaction type determines income or expense.
- Transaction ownership comes from the authenticated user.
- Clients cannot assign or change a transaction's user ID.
- List and summary queries are restricted to the current user.
- PATCH distinguishes omitted fields from explicit null values.
- Only the description can be cleared with null.
- The browser stores the access token in sessionStorage.

## Validation Status

Manually checked through Swagger UI and the web interface:

- Registration, login and authenticated user retrieval
- Transaction creation, editing and deletion
- Income and expense totals
- Data isolation between two users
- Rejection of access to another user's transactions
- Missing transaction responses after deletion

Automated tests have not been added yet.

## Current Scope

This is a deployed portfolio MVP. It does not yet include automated tests,
password recovery, refresh tokens, bank integrations or currency conversion.
