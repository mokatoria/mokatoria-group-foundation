import secrets
import hashlib
import hmac
import json
from urllib.parse import urlparse
from schema_upgrade import upgrade_payment_schema
import csv
import io
from functools import wraps


import requests
from decimal import Decimal
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    abort,
    session,
    Response,
)
from flask_wtf.csrf import CSRFProtect

from werkzeug.security import check_password_hash

from config import Config
from extensions import db
from models import Donation
from forms import DonationForm

csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    if app.config["PAYSTACK_MODE"] not in {"test", "live"}:
        raise RuntimeError("PAYSTACK_MODE must be test or live.")
    if app.config["DEMO_MODE"] and app.config["PAYSTACK_MODE"] == "live":
        raise RuntimeError("Demo mode cannot be used with live mode.")
    csrf.init_app(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        upgrade_payment_schema(db.engine)

    register_routes(app)

    return app


def paystack_request(app, method, path, payload=None):
    key = app.config["PAYSTACK_SECRET_KEY"]
    mode = app.config["PAYSTACK_MODE"]
    if mode not in {"test", "live"} or not key.startswith(f"sk_{mode}_"):
        raise RuntimeError("Paystack key must match PAYSTACK_MODE.")
    response = requests.request(
        method, "https://api.paystack.co" + path,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload, timeout=(5, 15),
    )
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or body.get("status") is not True or not isinstance(body.get("data"), dict):
        raise ValueError("Invalid Paystack response")
    return body["data"]


def minor_units(amount):
    value = Decimal(str(amount))
    if not value.is_finite() or value <= 0 or value != value.quantize(Decimal("0.01")):
        raise ValueError("Invalid donation amount")
    return int(value * 100)


def verify_donation(app, donation):
    if donation.payment_mode not in {"test", "live"} or donation.payment_mode != app.config["PAYSTACK_MODE"]:
        raise ValueError("Payment mode mismatch")
    data = paystack_request(app, "GET", "/transaction/verify/" + donation.paystack_reference)
    if (data.get("reference") != donation.paystack_reference
            or type(data.get("amount")) is not int
            or data["amount"] != minor_units(donation.amount)
            or data.get("currency") != donation.currency
            or data.get("domain") != donation.payment_mode
            or data.get("channel") != "card"):
        raise ValueError("Payment details mismatch")
    if data.get("status") != "success":
        return False
    # One atomic, idempotent update; a later verified success can settle a cancelled checkout.
    Donation.query.filter(Donation.id == donation.id, Donation.status != "completed").update(
        {Donation.status: "completed"}, synchronize_session="fetch")
    db.session.commit()
    return True


def admin_required(view):
    """
    Require an authenticated administrator.
    """
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return view(*args, **kwargs)

    return wrapped_view


def register_routes(app):

    @app.route("/favicon.ico")
    def favicon():
        return app.send_static_file("favicon.ico")


    @app.context_processor
    def search_metadata():
        public_pages = {"index", "projects", "donate", "contact"}
        descriptions = {
            "index": "Mokatoria Community Foundation supports children and families through clean water, food, education, and mental wellbeing. Based in Nairobi, Kenya.",
            "projects": "Explore the community projects of Mokatoria Community Foundation in water, nutrition, education, and mental wellbeing.",
            "donate": "Support Mokatoria Community Foundation through PayPal or a KES bank transfer. View receiving details and contact us to confirm your contribution.",
            "contact": "Contact Mokatoria Community Foundation at mokatoriafoundation@gmail.com or +254 743 563 077. Find us on Tom Mboya Street, Nairobi, Kenya.",
        }
        canonical = "https://mokatoriagroupfoundation.com" + request.path if request.endpoint in public_pages else None
        return {"canonical_url": canonical, "page_description": descriptions.get(request.endpoint, "Mokatoria Community Foundation"), "public_search_page": request.endpoint in public_pages}

    @app.route("/robots.txt")
    def robots():
        return Response("User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /thank-you/\nDisallow: /paystack/\nDisallow: /donation/\nSitemap: https://mokatoriagroupfoundation.com/sitemap.xml\n", mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap():
        from xml.etree.ElementTree import Element, SubElement, tostring
        root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for path in ("/", "/projects", "/donate", "/contact"):
            item = SubElement(root, "url")
            SubElement(item, "loc").text = "https://mokatoriagroupfoundation.com" + path
        return Response(tostring(root, encoding="utf-8", xml_declaration=True), mimetype="application/xml")

    @app.after_request
    def private_page_search_headers(response):
        if request.path.startswith(("/admin", "/thank-you", "/paystack", "/donation")):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    # ---------------------------------------------------------
    # ADMIN LOGIN
    # ---------------------------------------------------------

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():

        # If already logged in, go straight to dashboard.
        if session.get("admin_logged_in"):
            return redirect(url_for("admin_donations"))

        if request.method == "POST":

            username = request.form.get(
                "username",
                "",
            ).strip()

            password = request.form.get(
                "password",
                "",
            )

            valid_username = (
                username == app.config["ADMIN_USERNAME"]
            )

            valid_password = (
                bool(app.config["ADMIN_PASSWORD_HASH"])
                and check_password_hash(
                    app.config["ADMIN_PASSWORD_HASH"],
                    password,
                )
            )

            if valid_username and valid_password:
                session.clear()
                session["admin_logged_in"] = True

                return redirect(
                    url_for("admin_donations")
                )

            flash(
                "Invalid username or password.",
                "error",
            )

        return render_template(
            "admin_login.html"
        )


    # ---------------------------------------------------------
    # ADMIN LOGOUT
    # ---------------------------------------------------------

    @app.route("/admin/logout", methods=["POST"])
    def admin_logout():

        session.clear()

        return redirect(
            url_for("admin_login")
        )


    # ---------------------------------------------------------
    # PUBLIC HOME PAGE
    # ---------------------------------------------------------

    @app.route("/")
    def index():

        total = db.session.query(
            db.func.coalesce(
                db.func.sum(Donation.amount),
                0,
            )
        ).filter(
            Donation.status == "completed", Donation.currency == "KES", Donation.payment_mode == "live"
        ).scalar()

        count = Donation.query.filter_by(
            status="completed", currency="KES", payment_mode="live"
        ).count()

        return render_template(
            "index.html",
            total=total,
            count=count,
        )


    # ---------------------------------------------------------
    # CONTACT
    # ---------------------------------------------------------

    @app.route("/contact")
    def contact():

        return render_template(
            "contact.html"
        )


    # ---------------------------------------------------------
    # PROJECTS
    # ---------------------------------------------------------

    @app.route("/projects")
    def projects():

        return render_template(
            "projects.html"
        )


    # ---------------------------------------------------------
    # DONATION PAGE
    # ---------------------------------------------------------

    @app.route(
        "/donate",
        methods=["GET", "POST"],
    )
    def donate():

        # Payments are made externally and confirmed manually, never by a browser return.
        if request.method == "POST":
            flash("Please use the PayPal or bank-transfer instructions below.", "info")
            return redirect(url_for("donate"), code=303)
        return render_template("donate.html")

    @app.route("/paystack/callback")
    def paystack_callback():
        reference = request.args.get("reference", "")
        donation = Donation.query.filter_by(paystack_reference=reference).first_or_404()
        if donation.payment_mode == "demo":
            abort(400)
        session["donation_id"] = donation.id
        try:
            if verify_donation(app, donation):
                return redirect(url_for("thank_you", donation_id=donation.id))
        except (requests.RequestException, ValueError, RuntimeError, TypeError):
            app.logger.warning("Payment verification failed for donation %s", donation.id)
        return render_template("payment_pending.html", donation=donation), 202

    @app.route("/admin/donations/<int:donation_id>/verify", methods=["POST"])
    @admin_required
    def admin_verify(donation_id):
        donation = db.get_or_404(Donation, donation_id)
        if not donation.paystack_reference or donation.payment_mode not in {"test", "live"}:
            abort(400)
        try:
            confirmed = verify_donation(app, donation)
            flash("Payment confirmed." if confirmed else "Payment remains unconfirmed.", "info")
        except (requests.RequestException, ValueError, RuntimeError, TypeError):
            flash("Verification unavailable or details do not match. Record left unchanged.", "error")
        return redirect(url_for("admin_donations"))

    @app.route("/paystack/webhook", methods=["POST"])
    @csrf.exempt
    def paystack_webhook():
        # The only CSRF exemption: authenticated provider-to-server notifications.
        key = app.config["PAYSTACK_SECRET_KEY"]
        if not key or not key.startswith("sk_" + app.config["PAYSTACK_MODE"] + "_"):
            abort(503)
        signature = hmac.new(key.encode(), request.get_data(), hashlib.sha512).hexdigest()
        if not hmac.compare_digest(signature, request.headers.get("x-paystack-signature", "")):
            abort(401)
        event = request.get_json(silent=True)
        if not isinstance(event, dict):
            abort(400)
        if event.get("event") != "charge.success":
            return "", 200
        data = event.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("reference"), str):
            abort(400)
        donation = Donation.query.filter_by(paystack_reference=data["reference"]).first()
        if donation is None:
            return "", 200
        try:
            if not verify_donation(app, donation):
                abort(503)
        except (requests.RequestException, ValueError, RuntimeError, TypeError):
            abort(503)  # Provider can retry; never trust webhook amounts alone.
        return "", 200

    @app.route("/donation/cancel/<int:donation_id>", methods=["POST"])
    def donation_cancel(donation_id):
        if session.get("donation_id") != donation_id:
            abort(404)
        donation = db.get_or_404(Donation, donation_id)
        Donation.query.filter_by(id=donation.id, status="pending").update({Donation.status: "cancelled"})
        db.session.commit()
        flash("Checkout cancelled. A payment already sent can still be confirmed; contact us before retrying.", "info")
        return redirect(url_for("donate"))

    # ---------------------------------------------------------
    # THANK YOU
    # ---------------------------------------------------------

    @app.route(
        "/thank-you/<int:donation_id>"
    )
    def thank_you(donation_id):

        donation = db.get_or_404(Donation, donation_id)

        if session.get("donation_id") != donation_id or donation.status != "completed":
            abort(404)

        return render_template(
            "thank_you.html",
            donation=donation,
        )


    # ---------------------------------------------------------
    # ADMIN DONATION DASHBOARD
    # ---------------------------------------------------------

    @app.route("/admin/donations")
    @admin_required
    def admin_donations():

        donations = Donation.query.order_by(
            Donation.created_at.desc()
        ).all()

        completed_donations = [
            donation
            for donation in donations
            if donation.status == "completed" and donation.currency == "KES" and donation.payment_mode == "live"
        ]

        completed_total = sum(
            donation.amount
            for donation in completed_donations
        )

        completed_count = len(
            completed_donations
        )

        average_donation = (
            completed_total / completed_count
            if completed_count
            else 0
        )

        pending_count = sum(
            1
            for donation in donations
            if donation.status == "pending"
        )

        cancelled_count = sum(
            1
            for donation in donations
            if donation.status == "cancelled"
        )

        return render_template(
            "admin.html",
            donations=donations,
            completed_total=completed_total,
            completed_count=completed_count,
            average_donation=average_donation,
            pending_count=pending_count,
            cancelled_count=cancelled_count,
        )


    # ---------------------------------------------------------
    # ADMIN CSV EXPORT
    # ---------------------------------------------------------

    @app.route(
        "/admin/donations/export"
    )
    @admin_required
    def export_donations():

        donations = Donation.query.order_by(
            Donation.created_at.desc()
        ).all()

        output = io.StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "ID",
            "Name",
            "Email",
            "Amount",
            "Currency",
            "Mode",
            "Status",
            "Message",
            "Paystack Reference",
            "Date",
        ])

        for donation in donations:

            writer.writerow([
                donation.id,
                donation.name,
                donation.email,
                f"{donation.amount:.2f}",
                donation.currency,
                donation.payment_mode,
                donation.status,
                donation.message or "",
                donation.paystack_reference or "",
                donation.created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ])

        csv_data = output.getvalue()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": (
                    "attachment; "
                    "filename=donations.csv"
                )
            },
        )


import os

if os.getenv("FLASK_SKIP_STARTUP") != "1":
    app = create_app()

if __name__ == "__main__":
    app.run(debug=False, port=5000)