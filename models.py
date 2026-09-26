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

    # PayPal order ID used to connect the local donation
    # record with the PayPal checkout order.
    paypal_order_id = db.Column(db.String(200), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Donation {self.id} {self.name!r} ${self.amount:.2f} [{self.status}]>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "amount": self.amount,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }