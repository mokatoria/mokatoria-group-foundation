"""A shared, database-backed attempt budget for this single-admin website."""
import math
import time

from sqlalchemy import case, update
from sqlalchemy.exc import IntegrityError

from extensions import db

LIMIT = 5
WINDOW_SECONDS = 15 * 60


class AdminLoginBudget(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    window_started = db.Column(db.Float, nullable=False)
    attempts = db.Column(db.Integer, nullable=False)


def reserve_login_attempt(now=None):
    """Reserve before checking a password, atomically across app workers.

    A shared budget deliberately does not trust forwarded IP headers or store
    visitor addresses. Invalid usernames consume the same budget as valid ones.
    """
    now = time.time() if now is None else now
    if db.session.get(AdminLoginBudget, 'admin') is None:
        db.session.add(AdminLoginBudget(id='admin', window_started=now, attempts=0))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()  # Another worker initialized the same row.
    expired = AdminLoginBudget.window_started <= now - WINDOW_SECONDS
    result = db.session.execute(
        update(AdminLoginBudget)
        .where(AdminLoginBudget.id == 'admin')
        .where(expired | (AdminLoginBudget.attempts < LIMIT))
        .values(
            attempts=case((expired, 1), else_=AdminLoginBudget.attempts + 1),
            window_started=case((expired, now), else_=AdminLoginBudget.window_started),
        )
        .returning(AdminLoginBudget.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    db.session.commit()
    if result:
        return 0
    budget = db.session.get(AdminLoginBudget, 'admin')
    return max(1, math.ceil(budget.window_started + WINDOW_SECONDS - now))


def reset_login_attempts():
    db.session.execute(update(AdminLoginBudget).where(AdminLoginBudget.id == 'admin').values(attempts=0))
    db.session.commit()
