# Money Saver

MVP backend for a SaaS product that helps users plan financial goals, distribute savings, and understand projected completion dates.

## Current vertical slice

- FastAPI application.
- React + TypeScript frontend application in `frontend/`.
- Frontend dashboard for auth, goals, contributions, cashflow, exchange rates, scenarios, and projections.
- Responsive frontend layout verified at 360px mobile and 768px tablet widths.
- Accessibility pass for form labels, focus-visible states, skip navigation, and keyboard-friendly controls.
- Panel-level empty, loading, and error states across dashboard sections.
- PWA manifest and basic service worker for app-shell caching.
- SQLAlchemy persistence layer with a local SQLite default and PostgreSQL-ready configuration.
- Initial Alembic migration.
- User-scoped goals through `X-User-Id` for the current MVP API boundary.
- Domain calculation module independent from API and storage.
- Goal creation and updates.
- Goal archiving without deleting contribution history.
- Manual contributions.
- Contribution reversal for mistaken entries.
- Priority updates.
- Strict priority and proportional allocation strategies.
- Nearest-deadline allocation strategy with frontend selection.
- Smallest-goal-first allocation strategy with frontend selection.
- Custom fixed-amount allocation strategy with API validation and frontend editor.
- Read/update API for the active allocation strategy.
- Profile, income, expense, debt, and emergency fund inputs.
- Financial summary that calculates safe monthly savings capacity.
- Currencies and stored exchange rates.
- Conversion of financial summary inputs and goal contributions into the user's base currency.
- Monthly amount scenario simulation.
- One-time inflow scenario simulation.
- Skipped-months scenario simulation.
- Cautious, realistic, and optimistic scenario presets.
- Goal deadline probability based on cautious, realistic, and optimistic scenario outcomes.
- Goal projection explainability payload with date-driving factors and assumptions.
- JSON export of user-owned data.
- Frontend downloads the backend user-data export attachment directly without rebuilding JSON client-side.
- CSV export of goals and goal contributions.
- CSV export of goal contributions for a selected date period.
- CSV import of goals with row-level validation.
- CSV template download for goal imports.
- CSV import of historical goal contributions with row-level validation.
- CSV template download for historical contribution imports.
- Structured CSV import error details with row number, field, source value, and message.
- First-party product analytics events for core MVP actions.
- Basic MVP activity analytics dashboard from first-party product events.
- User-visible audit log viewer for recent financial data changes.
- Account deletion endpoint with credential anonymization and refresh-token revocation.
- In-app notifications scheduled automatically from the current financial plan.
- User-controlled notification settings.
- Notification delivery preferences by channel and frequency.
- Recurring savings rules that can be applied as real goal contributions.
- Monthly reports with contribution totals, goal-level progress, warnings, and recommendations.
- Goal price history with explainable target price updates.
- Pytest coverage for core planning rules.
- Planning edge-case coverage for zero available savings, already reached goals, and overdue hard deadlines.
- E2E API smoke coverage for authenticated goal creation, contribution, CSV export, and CSV import roundtrip.

## Run locally

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Open `http://127.0.0.1:8000/docs`.

Run the frontend:

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

Open `http://127.0.0.1:5173`.

The frontend uses `http://127.0.0.1:8001` by default. Override it with `VITE_API_BASE_URL` if needed.

Frontend MVP surfaces:

- Register/login.
- Installable PWA metadata and basic offline app shell.
- Dashboard summary.
- Create goals.
- Edit and archive goals.
- Expand goal cards to review remaining amount, deadlines, projections, required monthly funding, and notes.
- Add and reverse goal contributions.
- Add monthly income, expenses, and debt payments.
- Edit and delete income, expense, and debt entries.
- Add manual exchange rates.
- Run a monthly savings scenario.
- Run a one-time inflow scenario.
- Run a skipped-months scenario.
- Compare cautious, realistic, and optimistic scenario presets.
- Review scenario-based goal deadline probability.
- Review structured date drivers in expanded goal details.
- Choose strict priority or proportional allocation.
- Choose nearest-deadline allocation when dated goals should be funded first.
- Choose smallest-goal-first allocation to close smaller goals sooner.
- Choose fixed monthly amounts per goal for custom allocation.
- Edit proportional allocation percentages per goal.
- Review a monthly contribution calendar generated by the planning engine.
- Compare planned monthly contributions with actual saved amounts.
- Review and manage automatically scheduled plan notifications.
- Configure notification channels and delivery frequency.
- Toggle notification categories.
- Create, pause, apply, and delete recurring contribution rules.
- Update goal prices and review price change history.
- Review monthly progress reports.
- Review MVP activity analytics.
- Review recent audit log entries.
- Delete the current account from the sidebar.
- Export goals and contributions as CSV.
- Export contributions for a selected date period.
- Import goals from CSV.
- Download a goal import CSV template.
- Import historical goal contributions from CSV.
- Download a contribution import CSV template.
- Review projected goal dates.
- Export user data as a backend-generated JSON download.
- Use the dashboard on mobile and tablet layouts without overlapping controls or broken goal cards.
- Navigate core dashboard controls with keyboard focus, skip to main content, and use labeled compact forms.
- See loading and API failure states inside the affected dashboard panel instead of relying only on a global alert.

By default the app uses `sqlite:///./money_saver.db` for local development.
For PostgreSQL, set `DATABASE_URL` before running the app:

```powershell
$env:DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/money_saver"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe main.py
```

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

The E2E smoke test in `tests/test_e2e_smoke.py` covers the core MVP workflow through public API endpoints: auth, goal creation, contribution, CSV export, CSV goal import, CSV contribution import, and plan recalculation.

## MVP API notes

- Register with `POST /api/auth/register`.
- Login with `POST /api/auth/login`.
- Pass `Authorization: Bearer <access_token>` to scope goals, contributions, plans, and strategies.
- Delete the current account with `DELETE /api/me`; this soft-deletes the user, anonymizes credentials, and revokes active refresh tokens.
- Refresh access with `POST /api/auth/refresh`; refresh tokens are stored only as SHA-256 hashes.
- For local development, `DEV_AUTH_FALLBACK_ENABLED=true` allows `X-User-Id` and a demo user when no bearer token is sent.
- Set `DEV_AUTH_FALLBACK_ENABLED=false` and a strong `SECRET_KEY` outside local development.

Financial planning endpoints:

- `GET/PATCH /api/me/profile`
- `GET/POST /api/currencies`
- `GET/POST /api/exchange-rates`
- `GET/POST /api/analytics/events`
- `GET /api/analytics/summary`
- `GET /api/audit-log`
- `GET /api/export/user-data`
- `GET /api/export/goals.csv`
- `GET /api/export/contributions.csv`
- `GET /api/export/contributions.csv?from_date=2026-07-01&to_date=2026-07-31`
- `GET /api/import/goals-template.csv`
- `GET /api/import/contributions-template.csv`
- `POST /api/import/goals.csv`
- `POST /api/import/contributions.csv`
- CSV import responses include `errors` for backward-compatible text messages and `error_details` for structured row-level diagnostics.
- `GET /api/notifications` runs the simple daily in-app notification scheduler before returning notifications.
- `POST /api/notifications/generate` manually generates notifications from the current plan.
- `POST /api/notifications/{notification_id}/read`
- `POST /api/notifications/{notification_id}/dismiss`
- `GET/PATCH /api/notification-settings`
- `GET/POST/PATCH/DELETE /api/recurring-rules`
- `POST /api/recurring-rules/{rule_id}/apply`
- `GET/POST /api/goals/{goal_id}/price-history`
- `GET /api/reports/monthly`
- `GET/POST/PATCH/DELETE /api/incomes`
- `GET/POST/PATCH/DELETE /api/expenses`
- `GET/POST/PATCH/DELETE /api/debts`
- `DELETE /api/goals/{goal_id}` archives a goal and removes it from active lists and plan calculations.
- `GET/PUT /api/emergency-fund`
- `GET /api/financial-summary`
- `GET/POST /api/plan/strategy`
- `POST /api/contributions/{contribution_id}/reverse`

`GET /api/plan` now uses the financial summary's `effective_monthly_available_amount`.
If income/expense/debt/emergency data exists, the plan uses the lower value between the user's manual monthly savings amount and the calculated safe capacity.
Non-base-currency inputs are converted through the latest stored exchange rate. A rate means `1 base_currency = rate quote_currency`.
For example, `base_currency=EUR`, `quote_currency=USD`, `rate=1.20` means `100 EUR = 120 USD`.
If a needed rate is missing, the affected financial input is excluded from summary. Foreign-currency goals without a rate are skipped only in projections and returned as plan conflicts, so goals and monthly constraints remain editable.
Goal contributions keep the original operation amount, the applied rate, the amount in goal currency, and the amount in the user's base currency.

## Next engineering steps

1. Add richer notification scheduling.
2. Add stored report snapshots.
3. Add selected-period export for goal contributions.
4. Add price tracking by product URL.
