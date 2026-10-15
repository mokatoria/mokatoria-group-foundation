# Record received donations

1. Open /admin/login and sign in with the existing administrator credentials.
2. Select **Record received payment** in the donation dashboard.
3. Check the actual receiving account. Enter the donor name, optional email, receiving account, transaction reference, net amount credited, currency, and date received.
4. Confirm the receipt checkbox and save. A payment is recorded as completed only through the authenticated form.
5. Select **Print / Save as PDF** on the receipt. Receipts remain admin-only; save the PDF yourself if a donor requests a copy. The website does not email receipts.

The dashboard totals each currency separately, excludes test/demo payments, and labels old records as legacy. Existing historical amounts and payment identifiers are preserved. CSV exports include the receiving account, reference, received date and confirmation audit fields. Internal notes do not appear on receipts.

Duplicate transaction references are blocked within each receiving account, including differences in capitalization or surrounding spaces. Separate real transactions must have their own reference. There is no automatic payment-provider reconciliation, editing, or deletion in this release. Verify entries carefully before saving.

The database update adds nullable tracking fields and a unique reference index without removing old records. Admin pages require authentication, keep CSRF protection, and return no-store / noindex headers. Do not share administrator credentials or receipt-page links with donors.
