# Give Back visual upgrade

This version keeps the existing Flask + SQLite + Stripe architecture and upgrades the donor-facing experience.

## What changed
- Rebuilt the homepage with a stronger hero section and primary donation CTA.
- Added a polished visual identity using green, cream, gold accents, and editorial typography.
- Added impact, purpose, and final call-to-action sections.
- Added responsive layouts for tablet and mobile widths.
- Reworked the donation form with suggested amounts, clearer grouping, and better focus states.
- Added a clearer demo-mode notice so local testing is not confused with a real payment.
- Reworked the thank-you page into a donor confirmation experience.
- Added a richer footer and sticky navigation.
- Kept the existing Flask routes, database model, validation, and Stripe flow intact.

## Before going live
1. Replace the generic copy with your organization's real mission, impact stories, contact details, and legal information.
2. Add authentic project photography where appropriate.
3. Protect `/admin/donations` with authentication before deployment; it currently exposes donor information to anyone who knows the URL.
4. Use HTTPS and production Stripe keys only in the production environment.
5. Consider adding donation receipts and an explicit donor consent/privacy notice.
