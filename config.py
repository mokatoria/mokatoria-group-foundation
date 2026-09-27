import os
from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()


class Config:
    # =========================================================
    # APPLICATION SECURITY
    # =========================================================

    SECRET_KEY = os.environ.get("SECRET_KEY")

    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY must be configured in the environment."
        )

    # =========================================================
    # DATABASE
    # =========================================================
    #
    # Local development:
    #   Uses donations.db
    #
    # Production:
    #   Set DATABASE_URL to your PostgreSQL connection string.
    #

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(
            os.path.dirname(__file__),
            "donations.db",
        ),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================================================
    # PAYPAL
    # =========================================================

    PAYPAL_CLIENT_ID = os.environ.get(
        "PAYPAL_CLIENT_ID",
        "",
    )

    PAYPAL_CLIENT_SECRET = os.environ.get(
        "PAYPAL_CLIENT_SECRET",
        "",
    )

    PAYPAL_ENV = os.environ.get(
        "PAYPAL_ENV",
        "sandbox",
    ).lower()

    # The application is in demo mode only when PayPal
    # credentials have not been configured.
    DEMO_MODE = not bool(
        PAYPAL_CLIENT_ID
        and PAYPAL_CLIENT_SECRET
    )

    # =========================================================
    # ADMIN ACCOUNT
    # =========================================================

    ADMIN_USERNAME = os.environ.get(
        "ADMIN_USERNAME",
        "admin",
    )

    ADMIN_PASSWORD_HASH = os.environ.get(
        "ADMIN_PASSWORD_HASH",
        "",
    )

    # =========================================================
    # SESSION SECURITY
    # =========================================================
    #
    # These settings are appropriate for HTTPS production.
    # They are disabled for local HTTP development so that
    # the local admin login continues to work.
    #

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = (
        os.environ.get(
            "SESSION_COOKIE_SECURE",
            "false",
        ).lower()
        == "true"
    )
    SESSION_COOKIE_NAME = "mokatoria_session"
    PERMANENT_SESSION_LIFETIME = 3600

    # =========================================================
    # APPLICATION ENVIRONMENT
    # =========================================================

    ENVIRONMENT = os.environ.get(
        "APP_ENV",
        "development",
    ).lower()

    # =========================================================
    # PRODUCTION VALIDATION
    # =========================================================

    if ENVIRONMENT == "production":

        if not PAYPAL_CLIENT_ID:
            raise RuntimeError(
                "PAYPAL_CLIENT_ID must be configured "
                "in production."
            )

        if not PAYPAL_CLIENT_SECRET:
            raise RuntimeError(
                "PAYPAL_CLIENT_SECRET must be configured "
                "in production."
            )

        if PAYPAL_ENV != "live":
            raise RuntimeError(
                "PAYPAL_ENV must be set to 'live' "
                "in production."
            )

        if not ADMIN_PASSWORD_HASH:
            raise RuntimeError(
                "ADMIN_PASSWORD_HASH must be configured "
                "in production."
            )

        if not os.environ.get("DATABASE_URL"):
            raise RuntimeError(
                "DATABASE_URL must be configured "
                "in production."
            )

        if not SESSION_COOKIE_SECURE:
            raise RuntimeError(
                "SESSION_COOKIE_SECURE must be true "
                "in production."
            )