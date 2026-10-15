from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from decimal import Decimal, InvalidOperation

class DonationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    amount = DecimalField('Amount (KES)', places=None, validators=[DataRequired()])
    message = TextAreaField('Message (optional)', validators=[Length(max=500)])
    submit = SubmitField('Continue to card payment')

    def validate_amount(self, field):
        try:
            value = field.data
            if not value.is_finite() or value < 1 or value > 10000000 or value != value.quantize(Decimal('0.01')):
                raise ValueError()
        except (ValueError, InvalidOperation, AttributeError):
            raise ValidationError('Enter 1–10,000,000 KES with at most two decimal places.')
