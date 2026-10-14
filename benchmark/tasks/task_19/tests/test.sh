#!/usr/bin/env bash
set -e

cd /app/rails-app

echo "[*] Running database migration extraction tests..."

# Check if database.yml was updated
if [ ! -f "config/database.yml" ]; then
    echo "[✗] ERROR: config/database.yml not found"
    exit 1
fi

echo "[✓] Found config/database.yml"

# Check if user-service database entry was added
if grep -q "user-service\|user_service" config/database.yml; then
    echo "[✓] user-service database entry found in database.yml"
else
    echo "[✗] ERROR: user-service database entry not found in database.yml"
    exit 1
fi

# Check for new migrations
echo "[*] Checking for new migrations..."

MIGRATION_COUNT=$(find db/migrate -name "*user*service*" -o -name "*extract*users*" -o -name "*extract*orders*" 2>/dev/null | wc -l)

if [ "$MIGRATION_COUNT" -gt 0 ]; then
    echo "[✓] Found $MIGRATION_COUNT migration(s) for user-service"
else
    echo "[!] WARNING: No user-service migrations found"
    echo "    Expected: Migrations to recreate users and orders tables"
fi

# Check if migrations create users table
echo "[*] Checking users table migration..."

if grep -r "create_table.*users" db/migrate/*.rb 2>/dev/null | grep -v "20240101000001" | head -1; then
    echo "[✓] Users table migration found"
else
    echo "[!] WARNING: Users table migration may not be created"
fi

# Check if migrations create orders table
echo "[*] Checking orders table migration..."

if grep -r "create_table.*orders" db/migrate/*.rb 2>/dev/null | grep -v "20240101000002" | head -1; then
    echo "[✓] Orders table migration found"
else
    echo "[!] WARNING: Orders table migration may not be created"
fi

# Check for foreign key constraint
echo "[*] Checking for foreign key constraint preservation..."

if grep -r "foreign_key\|add_foreign_key\|references.*user" db/migrate/*.rb 2>/dev/null | grep -v "20240101000002" | head -1; then
    echo "[✓] Foreign key constraint found in migrations"
else
    echo "[!] WARNING: Foreign key constraint may not be preserved"
fi

# Check for data export/import scripts
echo "[*] Checking for data export/import..."

if [ -f "db/export_users_orders.sql" ] || [ -f "db/export_data.sql" ] || [ -f "scripts/export_data.sh" ] || [ -f "db/data/export.sql" ]; then
    echo "[✓] Data export script found"
else
    echo "[!] WARNING: Data export script may not be created"
fi

# Check if data files exist (simple dump)
echo "[*] Checking for data dump files..."

if [ -f "db/data/users.sql" ] && [ -f "db/data/orders.sql" ]; then
    echo "[✓] Data dump files found"
    
    # Check if data is present
    USER_COUNT=$(grep -c "INSERT INTO users" db/data/users.sql 2>/dev/null || echo "0")
    ORDER_COUNT=$(grep -c "INSERT INTO orders" db/data/orders.sql 2>/dev/null || echo "0")
    
    if [ "$USER_COUNT" -gt 0 ]; then
        echo "[✓] Users data dump contains $USER_COUNT insert statement(s)"
    fi
    
    if [ "$ORDER_COUNT" -gt 0 ]; then
        echo "[✓] Orders data dump contains $ORDER_COUNT insert statement(s)"
    fi
else
    echo "[!] WARNING: Data dump files may not be created"
fi

# Check for validation script or documentation
echo "[*] Checking for validation documentation..."

if [ -f "MIGRATION_NOTES.md" ] || [ -f "README_MIGRATION.md" ] || [ -f "docs/migration.md" ] || grep -r "validate\|validation\|staging" db/migrate/*.rb 2>/dev/null | head -1; then
    echo "[✓] Migration validation documentation found"
else
    echo "[!] WARNING: Migration validation documentation may be missing"
fi

# Validate migration structure
echo "[*] Validating migration structure..."

MIGRATION_FILES=$(ls -1 db/migrate/*.rb 2>/dev/null | wc -l)
echo "[✓] Found $MIGRATION_FILES migration file(s)"

# Check for users table in new migrations (excluding original)
if grep -l "create_table.*:users\|create_table.*\"users\"" db/migrate/*.rb 2>/dev/null | grep -v "20240101000001" | head -1 > /dev/null; then
    echo "[✓] Users table creation found in migrations"
else
    echo "[!] WARNING: Users table creation may be missing"
fi

# Check for orders table in new migrations (excluding original)
if grep -l "create_table.*:orders\|create_table.*\"orders\"" db/migrate/*.rb 2>/dev/null | grep -v "20240101000002" | head -1 > /dev/null; then
    echo "[✓] Orders table creation found in migrations"
else
    echo "[!] WARNING: Orders table creation may be missing"
fi

# Check for foreign key
if grep -l "foreign_key\|references.*:user\|references.*\"user\"" db/migrate/*.rb 2>/dev/null | grep -v "20240101000002" | head -1 > /dev/null; then
    echo "[✓] Foreign key constraint found in migrations"
else
    echo "[!] WARNING: Foreign key constraint may be missing"
fi

# Check database.yml structure
echo "[*] Validating database.yml structure..."

if grep -A 5 "user-service\|user_service" config/database.yml | grep -q "database\|adapter"; then
    echo "[✓] user-service database configuration appears complete"
else
    echo "[!] WARNING: user-service database configuration may be incomplete"
fi

# Summary
echo "[*] Summary:"
echo "    Migrations found: $MIGRATION_COUNT"
echo "    Data dump files: $(ls -1 db/data/*.sql 2>/dev/null | wc -l)"

echo "[✓] All tests completed!"
exit 0
