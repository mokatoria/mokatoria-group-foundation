from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, TextAreaField, SubmitField, SelectField, DateField, BooleanField
from wtforms.validators import DataRequired, Email, Length, ValidationError, Optional
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


class RecordPaymentForm(FlaskForm):
    name = StringField('Donor name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Donor email (optional)', validators=[Optional(), Email(), Length(max=120)])
    amount = DecimalField('Amount received', places=None, validators=[DataRequired()])
    currency = SelectField('Currency received', choices=[(c, c) for c in ['KES', 'USD', 'ILS', 'EUR', 'GBP', 'CAD', 'AUD', 'CHF', 'JPY', 'SEK', 'NOK', 'DKK', 'NZD', 'SGD', 'HKD']])
    payment_method = SelectField('Receiving account', choices=[('paypal', 'PayPal'), ('equity', 'Equity Bank'), ('neema', 'Neema')])
    payment_reference = StringField('Transaction / bank reference', validators=[DataRequired(), Length(max=120)])
    received_on = DateField('Date received', validators=[DataRequired()])
    message = TextAreaField('Internal note (optional)', validators=[Length(max=500)])
    confirmed = BooleanField('I checked the receiving account and confirmed this payment arrived.', validators=[DataRequired(message='Confirm receipt in the receiving account before recording this payment.')])
    submit = SubmitField('Record confirmed payment')

    def validate_amount(self, field):
        try:
            value = field.data
            if not value.is_finite() or value <= 0 or value > 10000000 or value != value.quantize(Decimal('0.01')):
                raise ValueError()
            if self.currency.data == 'JPY' and value != value.to_integral_value():
                raise ValueError()
        except (ValueError, InvalidOperation, AttributeError):
            raise ValidationError('Enter a positive amount up to 10,000,000 with at most two decimals (whole yen for JPY).')

    def validate_received_on(self, field):
        from datetime import datetime, timezone
        if field.data > datetime.now(timezone.utc).date():
            raise ValidationError('The received date cannot be in the future.')

    def validate_name(self, field):
        if not field.data.strip():
            raise ValidationError('Enter a donor name.')

    def validate_payment_reference(self, field):
        if not field.data.strip():
            raise ValidationError('Enter the transaction reference from the receiving account.')
