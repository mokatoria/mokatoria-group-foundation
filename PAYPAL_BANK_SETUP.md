# PayPal and bank transfers

The /donate page displays the provided PayPal recipient email and Equity Bank receiving details. The PayPal button opens PayPal; the donor enters the displayed email there. This is not automated PayPal checkout.

Restart the Flask app to load the changes. No Paystack key is required for the donation page. Existing donation records, administration, and legacy Paystack verification routes remain available for previous payments.

New external payments do not automatically create database records, update totals, or show a paid thank-you page. Confirm receipt in the actual PayPal or bank account and maintain a manual record. Never treat a screenshot or browser return as payment proof.

Bank receiving currency is KES, confirmed by the account holder. Confirm the account details with the bank before sharing the site internationally.

Backup: backup_before_paypal_bank_20261015 (application files only; database unchanged).
