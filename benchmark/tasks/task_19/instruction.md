0. Read `./rails-app/README.md` first for an overview of the project.

1. Read `./rails-app/config/database.yml` to understand its structure, then add a `user_service` entry that:
- Inherits from `<<: *default`
- Sets a distinct `database` name (e.g. `user_service_db`)
- Includes `host` and `port` fields

2. Add extraction migrations in `db/migrate/`
Read the existing migrations (`20240101000001_*` and `20240101000002_*`) to get the schema, then create new migration file(s) with a later timestamp (e.g. `20240201000001`) that recreate:
- `users` table (email, name, password_digest, timestamps, unique index on email)
- `orders` table (user reference with foreign key, total, status, timestamps, indexes)

3. (Optional) Create data dump files
Add `db/data/users.sql` and `db/data/orders.sql` with sample `INSERT INTO` statements.
