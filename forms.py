from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Email, NumberRange, Length, Optional


class DonationForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    amount = FloatField(
        "Amount (USD)",
        validators=[DataRequired(), NumberRange(min=1, max=100000, message="Enter an amount between $1 and $100,000")],
    )
    message = TextAreaField("Message (optional)", validators=[Optional(), Length(max=500)])
