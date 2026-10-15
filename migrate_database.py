"""Add columns without changing historical amounts or removing historical PayPal IDs."""
from flask import Flask
from sqlalchemy import inspect, text
from config import Config
from extensions import db
import models

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
with app.app_context():
    inspector = inspect(db.engine)
    if 'donation' not in inspector.get_table_names():
        raise SystemExit('No donation table found. Check DATABASE_URL; new installs need no migration.')
    columns = {c['name']: c for c in inspector.get_columns('donation')}
    required = {'id', 'name', 'email', 'amount', 'message', 'status', 'created_at'}
    if not required.issubset(columns):
        raise SystemExit('Unrecognized legacy schema. Supply original models.py before migration.')
    if db.engine.dialect.name != 'sqlite':
        raise SystemExit('This migration supports SQLite only. Use a reviewed migration for other databases.')
    if 'paypal_order_id' in columns and not columns['paypal_order_id']['nullable']:
        raise SystemExit('Legacy paypal_order_id is required: a reviewed table migration is needed.')
    with db.engine.begin() as conn:
        for name, ddl in {
            'currency': "VARCHAR(3) NOT NULL DEFAULT 'USD'",
            'payment_mode': "VARCHAR(20) NOT NULL DEFAULT 'legacy'",
            'paystack_reference': 'VARCHAR(100)',
        }.items():
            if name not in columns:
                conn.execute(text(f'ALTER TABLE donation ADD COLUMN {name} {ddl}'))
        conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_donation_paystack_reference ON donation(paystack_reference)'))
    print('Migration complete. Historical USD rows and PayPal IDs retained; new donations explicitly use KES.')
