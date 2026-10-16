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
    assert '00151432' in html and 'Neema · Israel' in html
    assert 'Transfers from Israeli banks only.' in html
    assert 'confirm the correct deposit instructions directly with Neema' in html
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


def admin_form(client):
    with client.session_transaction() as session:
        session['admin_logged_in'] = True
        session['admin_username'] = 'test-admin'
    response = client.get('/admin/donations/new')
    assert response.status_code == 200
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.get_data(as_text=True)).group(1)


def payment_data(client, **changes):
    from datetime import datetime, timezone
    data = dict(csrf_token=admin_form(client), name='Test Donor', email='donor@example.com',
                amount='12.34', currency='USD', payment_method='paypal',
                payment_reference='txn-123', received_on=datetime.now(timezone.utc).date().isoformat(),
                confirmed='y', message='Private internal note')
    data.update(changes)
    return data


def test_manual_payment_requires_admin_and_csrf(client, app):
    assert client.get('/admin/donations/new').status_code == 302
    assert client.get('/admin/donations/1/receipt').status_code == 302
    assert client.post('/admin/donations/new', data={}).status_code == 400
    admin_form(client)
    assert client.post('/admin/donations/new', data={'name': 'Fake'}).status_code == 400
    with app.app_context():
        assert Donation.query.count() == 0


def test_record_payment_duplicate_receipt_totals_and_privacy(client, app):
    data = payment_data(client)
    response = client.post('/admin/donations/new', data=data)
    assert response.status_code == 303
    receipt_url = response.headers['Location']
    receipt = client.get(receipt_url)
    assert receipt.status_code == 200 and b'USD 12.34' in receipt.data
    assert b'Private internal note' not in receipt.data
    assert receipt.headers['Cache-Control'] == 'no-store'
    with app.app_context():
        donation = Donation.query.one()
        assert donation.status == 'completed' and donation.payment_mode == 'manual'
        assert donation.payment_reference == 'TXN-123'
        assert donation.confirmed_by == 'test-admin' and donation.confirmed_at
    data['payment_reference'] = ' TxN-123 '
    duplicate = client.post('/admin/donations/new', data=data)
    assert duplicate.status_code == 200 and b'already recorded' in duplicate.data
    client.post('/admin/donations/new', data=payment_data(client, currency='KES', amount='500', payment_method='equity'))
    dashboard = client.get('/admin/donations')
    assert b'USD received' in dashboard.data and b'KES received' in dashboard.data
    assert b'12.34' in dashboard.data and b'500.00' in dashboard.data
    csv = client.get('/admin/donations/export')
    assert b'Payment reference' in csv.data and b'TXN-123' in csv.data
    with client.session_transaction() as session:
        session.clear()
    assert client.get(receipt_url).status_code == 302
    for path in ['/', '/donate']:
        html = client.get(path).data
        assert b'Test Donor' not in html and b'txn-123' not in html
        assert b'Record received payment' not in html


@pytest.mark.parametrize('changes', [
    {'amount': '-1'}, {'amount': 'NaN'}, {'amount': '1.234'},
    {'confirmed': ''}, {'payment_reference': '   '}, {'name': '   '},
    {'currency': 'XXX'}, {'payment_method': 'unknown'}, {'received_on': '2999-01-01'},
    {'currency': 'JPY', 'amount': '1.23'},
])
def test_invalid_manual_records_are_not_saved(client, app, changes):
    response = client.post('/admin/donations/new', data=payment_data(client, **changes))
    assert response.status_code == 200
    with app.app_context():
        assert Donation.query.count() == 0


def test_translation_only_public_pages_and_safe_urls(client):
    from urllib.parse import urlparse, parse_qs
    for page, path in [('index','/'), ('donate','/donate'), ('contact','/contact'), ('projects','/projects')]:
        html = client.get(path).get_data(as_text=True)
        assert 'aria-label="Translate website"' in html and 'Kiswahili' in html
        assert 'Language / Lugha' not in html and 'Automatic translation' not in html
        response = client.get('/translate', query_string={'page':page,'language':'sw','email':'private@example.com'})
        assert response.status_code == 302
        dest = urlparse(response.headers['Location'])
        assert dest.hostname == 'translate.google.com'
        assert parse_qs(dest.query)['u'] == ['https://mokatoriagroupfoundation.com'+path]
        assert 'private' not in response.headers['Location']
    assert '<details class="translation-menu' not in client.get('/admin/login').get_data(as_text=True)
    admin_form(client)
    assert '<details class="translation-menu' not in client.get('/admin/donations/new').get_data(as_text=True)
    assert client.get('/translate?page=admin_donations&language=sw').status_code == 400
    assert client.get('/translate?page=https://evil.example&language=sw').status_code == 400
    assert client.get('/translate?language=invalid').status_code == 400
    assert client.get('/translate?language=en&page=donate').headers['Location'] == '/donate'
    assert 'translate="no"' in client.get('/donate').get_data(as_text=True)


def test_language_choices_cannot_be_rewritten_as_proxy_links(client):
    html = client.get('/contact').get_data(as_text=True)
    assert 'data-public-url="https://mokatoriagroupfoundation.com/contact"' in html
    assert '<button type="button" data-language="en" lang="en">English</button>' in html
    assert '<button type="button" data-language="sw"' in html
    assert 'js/language-switcher.js' in html
    menu = html.split('class="translation-choices"',1)[1].split('</div>',1)[0]
    assert '<a ' not in menu and 'target="_blank"' not in menu
