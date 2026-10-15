import os
import sys
import json
import re
from xml.etree import ElementTree

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['FLASK_SKIP_STARTUP'] = '1'
from app import create_app
from config import Config
from extensions import db
from models import Donation
from schema_upgrade import upgrade_payment_schema


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.mark.parametrize('path', ['/', '/projects', '/donate', '/contact'])
def test_public_identity_and_search_metadata(client, path):
    response = client.get(path)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Mokatoria Community Foundation' in html
    assert 'Give Back' not in html
    assert 'rel="canonical" href="https://mokatoriagroupfoundation.com' + path + '"' in html
    data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    assert data['email'] == 'mokatoriafoundation@gmail.com'


def test_external_payment_details_and_no_false_confirmation(client, app):
    html = client.get('/donate').get_data(as_text=True)
    assert 'p84669324@gmail.com' in html and '7770179484119' in html
    assert '<details class="payment-option bank-option">' in html
    assert 'EQBLKENA' in html and 'KES (Kenyan shillings)' in html
    # Unauthenticated submissions must still require a CSRF token.
    assert client.post('/donate', data={'amount': '100'}).status_code == 400
    with app.app_context():
        assert Donation.query.count() == 0
    assert client.get('/admin/donations').status_code == 302
    assert client.get('/admin/login').headers['X-Robots-Tag'] == 'noindex, nofollow'


def test_sitemap_and_robots(client):
    root = ElementTree.fromstring(client.get('/sitemap.xml').data)
    urls = {item[0].text for item in root}
    assert urls == {'https://mokatoriagroupfoundation.com' + path for path in ['/', '/projects', '/donate', '/contact']}
    assert b'Sitemap: https://mokatoriagroupfoundation.com/sitemap.xml' in client.get('/robots.txt').data


def test_legacy_donation_schema_upgrade_preserves_history():
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE donation (id INTEGER PRIMARY KEY, amount FLOAT, status TEXT, paypal_order_id TEXT)'))
        connection.execute(text("INSERT INTO donation VALUES (1, 25.5, 'completed', 'old-paypal-order')"))
    upgrade_payment_schema(engine)
    upgrade_payment_schema(engine)
    with engine.connect() as connection:
        row = connection.execute(text('SELECT * FROM donation')).mappings().one()
        assert row['amount'] == 25.5 and row['status'] == 'completed'
        assert row['paypal_order_id'] == 'old-paypal-order'
        assert row['currency'] == 'USD' and row['payment_mode'] == 'legacy'
