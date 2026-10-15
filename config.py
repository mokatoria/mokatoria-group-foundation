import os
from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


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

    # Render PostgreSQL URLs use the installed psycopg 3 driver.
    if SQLALCHEMY_DATABASE_URI.startswith(("postgres://", "postgresql://")):
        SQLALCHEMY_DATABASE_URI = "postgresql+psycopg://" + SQLALCHEMY_DATABASE_URI.split("://", 1)[1]

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================================================
    # PAYSTACK
    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
    PAYSTACK_MODE = os.getenv("PAYSTACK_MODE", "test").lower()
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5000")
    MAX_CONTENT_LENGTH = 65536

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

        if DEMO_MODE:
            raise RuntimeError("Demo mode must be disabled in production.")

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