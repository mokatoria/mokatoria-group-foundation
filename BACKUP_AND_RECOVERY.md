# Donation records: backup and recovery

## Current status

The admin dashboard provides a private CSV export of donation records. This is useful for reconciliation, but is not a complete database backup. Automatic database backups have not been verified or enabled by this website update.

## Routine record export

After recording payments, sign in to the admin dashboard and download the donation CSV. Keep a dated copy in a private, access-controlled location. It contains donor information: do not put it in the public website folder or a public repository.

## Hosted database backup

In Render, open the database resource linked to the web service, then check its actual plan and Recovery/Backups options. A free web service does not establish which database plan is in use.

For paid Render Postgres, check the available point-in-time recovery window and create a logical backup export. Download a copy to private storage. Free Render Postgres does not provide managed backups; use a PostgreSQL `pg_dump` export through the database's connection instructions, or choose a plan with managed recovery. If the database is hosted elsewhere, use that provider's backup facilities instead.

Keep database connection passwords out of screenshots, chat, public files, and version control.

Official references:
- https://render.com/docs/postgresql-backups
- https://render.com/docs/free

## Recovery check

Restore a backup into a separate, empty test database first. Never test recovery by overwriting the live database. Check record counts, amounts and currencies, payment references, dates, and admin access. Only switch the live site after the restored data has been reviewed and any payments recorded since the backup have been reconciled.

Website source history and local application copies do not back up the live donation database.
