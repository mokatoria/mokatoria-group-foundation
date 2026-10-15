"""Add payment metadata without changing legacy amounts, statuses or PayPal IDs."""
from sqlalchemy import inspect, text


def upgrade_payment_schema(engine):
    if engine.dialect.name not in {'sqlite', 'postgresql'}:
        raise RuntimeError('Payment schema upgrade supports SQLite and PostgreSQL only.')
    with engine.begin() as connection:
        # Serialize simultaneous Gunicorn worker starts on PostgreSQL.
        if engine.dialect.name == 'postgresql':
            connection.execute(text('SELECT pg_advisory_xact_lock(6841092026)'))
        columns = {column['name'] for column in inspect(connection).get_columns('donation')}
        for name, definition in {
            'currency': "VARCHAR(3) NOT NULL DEFAULT 'USD'",
            'payment_mode': "VARCHAR(20) NOT NULL DEFAULT 'legacy'",
            'paystack_reference': 'VARCHAR(100)',
            'payment_method': 'VARCHAR(20)',
            'payment_reference': 'VARCHAR(120)',
            'received_on': 'DATE',
            'confirmed_at': 'TIMESTAMP',
            'confirmed_by': 'VARCHAR(120)',
        }.items():
            if name not in columns:
                connection.execute(text(f'ALTER TABLE donation ADD COLUMN {name} {definition}'))
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_donation_paystack_reference ON donation (paystack_reference)'))

        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_donation_manual_reference ON donation (payment_method, payment_reference)'))
