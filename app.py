import base64
import csv
import io
from functools import wraps


import requests
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
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
    csrf.init_app(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)

    return app


def get_paypal_base_url(app):
    """Return the correct PayPal API URL for the current environment."""
    if app.config["PAYPAL_ENV"].lower() == "live":
        return "https://api-m.paypal.com"

    return "https://api-m.sandbox.paypal.com"


def get_paypal_access_token(app):
    """
    Get a PayPal OAuth access token using the Client ID and Secret.
    """
    client_id = app.config["PAYPAL_CLIENT_ID"]
    client_secret = app.config["PAYPAL_CLIENT_SECRET"]

    if not client_id or not client_secret:
        raise RuntimeError("PayPal credentials are not configured.")

    credentials = f"{client_id}:{client_secret}"

    encoded_credentials = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")

    response = requests.post(
        f"{get_paypal_base_url(app)}/v1/oauth2/token",
        headers={
            "Accept": "application/json",
            "Accept-Language": "en_US",
            "Authorization": f"Basic {encoded_credentials}",
        },
        data={
            "grant_type": "client_credentials",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()["access_token"]


def create_paypal_order(app, donation):
    """
    Create a PayPal order for the donation.
    """
    access_token = get_paypal_access_token(app)

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": str(donation.id),
                "description": "Donation to Mokatoria Group Foundation",
                "custom_id": str(donation.id),
                "amount": {
                    "currency_code": "USD",
                    "value": f"{donation.amount:.2f}",
                },
            }
        ],
    }

    response = requests.post(
        f"{get_paypal_base_url(app)}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def capture_paypal_order(app, order_id):
    """
    Capture an approved PayPal order.
    """
    access_token = get_paypal_access_token(app)

    response = requests.post(
        f"{get_paypal_base_url(app)}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json={},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


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

    @app.route("/admin/logout")
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
            Donation.status == "completed"
        ).scalar()

        count = Donation.query.filter_by(
            status="completed"
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

        form = DonationForm()

        if form.validate_on_submit():

            donation = Donation(
                name=form.name.data.strip(),
                email=form.email.data.strip(),
                amount=round(
                    form.amount.data,
                    2,
                ),
                message=(
                    form.message.data or ""
                ).strip(),
                status="pending",
            )

            db.session.add(donation)
            db.session.commit()

            # Local demo mode if PayPal credentials
            # are not configured.
            if app.config["DEMO_MODE"]:

                donation.status = "completed"

                db.session.commit()

                return redirect(
                    url_for(
                        "thank_you",
                        donation_id=donation.id,
                    )
                )

            try:

                order = create_paypal_order(
                    app,
                    donation,
                )

                donation.paypal_order_id = order["id"]

                db.session.commit()

                return redirect(
                    url_for(
                        "paypal_checkout",
                        donation_id=donation.id,
                    )
                )

            except Exception as exc:

                app.logger.exception(
                    "PayPal order creation failed: %s",
                    exc,
                )

                donation.status = "cancelled"

                db.session.commit()

                flash(
                    "We couldn't start the payment process. "
                    "Please try again.",
                    "error",
                )

                return redirect(
                    url_for("donate")
                )

        return render_template(
            "donate.html",
            form=form,
            demo_mode=app.config["DEMO_MODE"],
            paypal_client_id=app.config[
                "PAYPAL_CLIENT_ID"
            ],
        )


    # ---------------------------------------------------------
    # PAYPAL CHECKOUT PAGE
    # ---------------------------------------------------------

    @app.route(
        "/paypal/checkout/<int:donation_id>"
    )
    def paypal_checkout(donation_id):

        donation = Donation.query.get_or_404(
            donation_id
        )

        if not donation.paypal_order_id:

            flash(
                "The PayPal payment could not be started.",
                "error",
            )

            return redirect(
                url_for("donate")
            )

        return render_template(
            "paypal_checkout.html",
            donation=donation,
            paypal_client_id=app.config[
                "PAYPAL_CLIENT_ID"
            ],
        )


    # ---------------------------------------------------------
    # PAYPAL CAPTURE
    # ---------------------------------------------------------

    @app.route(
        "/paypal/capture",
        methods=["POST"],
    )
    def paypal_capture():

        data = request.get_json(
            silent=True
        ) or {}

        order_id = data.get(
            "order_id"
        )

        if not order_id:

            return jsonify({
                "success": False,
                "error": "Missing PayPal order ID.",
            }), 400

        donation = Donation.query.filter_by(
            paypal_order_id=order_id
        ).first()

        if not donation:

            return jsonify({
                "success": False,
                "error": "Donation not found.",
            }), 404

        if donation.status == "completed":

            return jsonify({
                "success": True,
                "donation_id": donation.id,
            })

        try:

            result = capture_paypal_order(
                app,
                order_id,
            )

            if result.get("status") == "COMPLETED":

                donation.status = "completed"

                db.session.commit()

                return jsonify({
                    "success": True,
                    "donation_id": donation.id,
                })

            app.logger.warning(
                "PayPal order %s was not completed: %s",
                order_id,
                result,
            )

            return jsonify({
                "success": False,
                "error": (
                    "PayPal did not confirm the payment."
                ),
            }), 400

        except requests.HTTPError as exc:

            app.logger.exception(
                "PayPal capture failed: %s",
                exc,
            )

            return jsonify({
                "success": False,
                "error": (
                    "PayPal could not complete the payment."
                ),
            }), 400

        except Exception as exc:

            app.logger.exception(
                "Unexpected PayPal capture error: %s",
                exc,
            )

            return jsonify({
                "success": False,
                "error": (
                    "An unexpected payment error occurred."
                ),
            }), 500


    # ---------------------------------------------------------
    # CANCEL DONATION
    # ---------------------------------------------------------

    @app.route(
        "/donation/cancel/<int:donation_id>"
    )
    def donation_cancel(donation_id):

        donation = Donation.query.get_or_404(
            donation_id
        )

        if donation.status == "pending":

            donation.status = "cancelled"

            db.session.commit()

        flash(
            "Your donation was cancelled. "
            "No payment was taken.",
            "info",
        )

        return redirect(
            url_for("donate")
        )


    # ---------------------------------------------------------
    # THANK YOU
    # ---------------------------------------------------------

    @app.route(
        "/thank-you/<int:donation_id>"
    )
    def thank_you(donation_id):

        donation = Donation.query.get_or_404(
            donation_id
        )

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
            if donation.status == "completed"
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
            "Amount USD",
            "Status",
            "Message",
            "PayPal Order ID",
            "Date",
        ])

        for donation in donations:

            writer.writerow([
                donation.id,
                donation.name,
                donation.email,
                f"{donation.amount:.2f}",
                donation.status,
                donation.message or "",
                donation.paypal_order_id or "",
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


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)