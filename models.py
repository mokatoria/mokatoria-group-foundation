from datetime import datetime

from extensions import db


class Donation(db.Model):
    """
    One donation record.

    status flow:
      pending    -> donation created, payment not yet confirmed
      completed  -> payment successfully captured
      cancelled  -> donor abandoned or cancelled checkout
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False)

    currency = db.Column(db.String(3), nullable=False, default="KES")
    payment_mode = db.Column(db.String(20), nullable=False)
    paystack_reference = db.Column(db.String(100), nullable=True, unique=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Donation {self.id} {self.name!r} {self.currency} {self.amount:.2f} [{self.status}]>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "amount": self.amount,
            "currency": self.currency,
            "payment_mode": self.payment_mode,
            "paystack_reference": self.paystack_reference,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }