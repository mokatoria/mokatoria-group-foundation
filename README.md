# Give Back — Donation Site (MVP)

A minimal, professional donation website: Flask + SQLite + a Stripe Checkout
integration that's safe to grow into production. Runs immediately in
**demo mode** (no payment account needed) so you can build and test the
whole flow before touching real payments.

## Project structure

```
donation_site/
├── app.py              # Flask app factory + all routes
├── config.py            # Settings, loaded from environment variables
├── extensions.py        # SQLAlchemy db instance
├── models.py             # Donation table
├── forms.py               # Server-side form validation (Flask-WTF)
├── requirements.txt
├── .env.example          # Copy to .env and fill in
├── .gitignore
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── donate.html
│   ├── thank_you.html
│   └── admin.html
├── static/css/style.css
└── tests/test_app.py     # pytest suite
```

## 1. Open the project in PyCharm

1. Unzip the project, then in PyCharm: **File → Open** and select the
   `donation_site` folder.
2. Set up an interpreter: **PyCharm → Settings/Preferences → Project:
   donation_site → Python Interpreter → Add Interpreter → Add Local
   Interpreter → Virtualenv Environment → New**. Base it on Python 3.10+.
   PyCharm will create a `.venv` inside the project.
3. Open the built-in terminal (**View → Tool Windows → Terminal**) — it
   will already be using that virtualenv — and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

   Open `.env` in PyCharm and set `SECRET_KEY` to any long random string.
   Leave the `STRIPE_*` fields blank for now — that's what puts the app in
   demo mode.

## 2. Run it locally

**From the terminal:**
```bash
python app.py
```
Then open `http://127.0.0.1:5000` in your browser.

**From PyCharm's Run button (recommended once set up):**
1. Right-click `app.py` → **Run 'app'**.
2. PyCharm creates a Run Configuration automatically. You can rename it
   ("Flask Dev Server") via **Run → Edit Configurations**.
3. Click the green ▶ any time after that to start the server, and the red
   ■ to stop it.

The first run creates `donations.db` (SQLite) automatically — nothing else
to set up.

## 3. Try the flow

1. Visit `/` — you'll see the homepage with a running total (starts at $0).
2. Click **Donate**, fill in the form, submit.
3. Because no Stripe key is set, the donation is recorded immediately as
   `completed` and you land on a thank-you page.
4. Go back to `/` — the total updates.
5. Visit `/admin/donations` to see every recorded donation in a table.
   (This view has no login yet — see "Before going live" below.)

## 4. Testing in PyCharm

The `tests/test_app.py` file uses `pytest` and an in-memory SQLite
database, so it never touches your real `donations.db`.

**Run all tests:**
- Right-click the `tests` folder → **Run 'pytest in tests'**.
- Or from the terminal: `pytest -v`

**Run a single test:** right-click a specific `def test_...` function in
the editor gutter → **Run**.

If PyCharm doesn't offer the pytest option, set it as the default test
runner: **Settings → Tools → Python Integrated Tools → Testing → Default
test runner → pytest**.

What's covered: the homepage loads, the donate form loads, a valid
donation is recorded and shows a thank-you page, an invalid amount is
rejected, an invalid email is rejected, and the homepage total reflects
completed donations.

## 5. Debugging in PyCharm

1. Click in the left gutter next to any line in `app.py` (e.g. inside the
   `donate()` view) to set a breakpoint — a red dot appears.
2. Right-click `app.py` → **Debug 'app'** (instead of Run). The terminal
   shows a debugger icon instead of a plain run icon.
3. Trigger that code path in the browser (e.g. submit the donation form).
   Execution pauses at your breakpoint.
4. Use the **Debugger** tool window: **Step Over (F8)** to go line by
   line, **Step Into (F7)** to follow into a function call (e.g. into
   `stripe.checkout.Session.create`), and inspect variables like `form`
   or `donation` in the **Variables** pane.
5. To inspect the database directly, open **View → Tool Windows →
   Database**, click **+ → Data Source → SQLite**, and point it at
   `donations.db` in the project root. You can then browse the
   `donation` table without writing SQL.

Flask's debug mode (`app.run(debug=True)`) also gives you an interactive
in-browser traceback if an unhandled exception occurs — useful for quick
checks, but PyCharm's debugger is better for stepping through logic.

## 6. Payment integration plan (safe by design)

The app never touches raw card numbers, which keeps you out of PCI-DSS
scope almost entirely. The plan:

- **Stripe Checkout** (hosted payment page): the donor is redirected to a
  Stripe-hosted page to enter card details. Your server never sees or
  stores card numbers — Stripe does.
- **Test mode first**: create a free Stripe account, then use its test-mode
  API keys (they start with `sk_test_` / `pk_test_`) in your `.env`.
  Test-mode payments use fake card numbers (e.g. `4242 4242 4242 4242`)
  and never move real money.
- **Webhook confirmation**: the `/webhook/stripe` route is already wired
  up to receive a server-to-server event from Stripe when a payment
  actually succeeds (`checkout.session.completed`), rather than trusting
  the browser redirect alone — a donor could otherwise fake landing on
  the success page without paying. For local testing, use the
  [Stripe CLI](https://stripe.com/docs/stripe-cli) (`stripe listen
  --forward-to localhost:5000/webhook/stripe`) to receive real webhook
  events on your machine.
- **Secrets stay in `.env`**, which is git-ignored — never commit API
  keys or `SECRET_KEY` to version control.
- **Switching on real payments**: once you have real (`sk_live_...`)
  Stripe keys, drop them into your production environment's variables
  (not `.env` on a shared machine) and `DEMO_MODE` turns off automatically.

### Before going live (not yet in this MVP)
- Add authentication to `/admin/donations` (e.g. Flask-Login) — right now
  anyone who knows the URL can view donor names/emails.
- Serve over HTTPS (required by Stripe in production, and for basic
  donor trust).
- Add rate limiting to `/donate` to reduce spam/abuse.
- Consider receipt emails (e.g. via Flask-Mail) after a completed donation.
- Move off SQLite to Postgres if you expect meaningful concurrent traffic.

## 7. Extending it

- Add suggested donation amount buttons ($10/$25/$50/$100) to `donate.html`.
- Add a recurring/monthly donation option (Stripe Checkout supports
  subscription mode).
- Add a public donor wall (respecting an opt-in "show my name" checkbox).
