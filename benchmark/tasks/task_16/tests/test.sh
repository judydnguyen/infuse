#!/usr/bin/env bash
set -e

cd /app/price-monitoring

echo "[*] Running price monitoring automation tests..."

# Check if required directories exist
if [ ! -d "data" ]; then
    echo "[✗] ERROR: data directory not found"
    exit 1
fi

if [ ! -d "reports" ]; then
    echo "[✗] ERROR: reports directory not found"
    exit 1
fi

echo "[✓] Required directories exist"

# Check if yesterday's data exists (look for any JSON file that's not today's date)
# Today is February 1, 2024 per instruction
TODAY="2024-02-01"
YESTERDAY_FILES=$(find data -name "*.json" -type f ! -name "${TODAY}.json" 2>/dev/null | head -1)

if [ -z "$YESTERDAY_FILES" ]; then
    echo "[✗] ERROR: No previous price data found in data/ directory"
    echo "    Expected at least one JSON file with yesterday's date"
    exit 1
fi

YESTERDAY_FILE=$(basename "$YESTERDAY_FILES")
echo "[✓] Previous price data found: $YESTERDAY_FILE"

# Check if today's data was scraped
if [ ! -f "data/${TODAY}.json" ]; then
    echo "[✗] ERROR: Today's price data not found (data/${TODAY}.json)"
    echo "    Price scraping may not have been executed"
    exit 1
fi

echo "[✓] Today's price data found (data/${TODAY}.json)"

# Validate today's data is valid JSON
if ! python3 -m json.tool "data/${TODAY}.json" > /dev/null 2>&1; then
    echo "[✗] ERROR: Today's price data is not valid JSON"
    exit 1
fi

echo "[✓] Today's price data is valid JSON"

# Check if report was generated
REPORT_FOUND=false
for report in reports/*.txt reports/*.json reports/*.html reports/*.md; do
    if [ -f "$report" ]; then
        echo "[✓] Found report: $report"
        REPORT_FOUND=true
        break
    fi
done

if [ "$REPORT_FOUND" = false ]; then
    echo "[✗] ERROR: No report found in reports/ directory"
    exit 1
fi

# Check if report contains price drop information
echo "[*] Checking report content..."

python3 << 'EOF'
import json
import os
import glob
import sys
from datetime import datetime

# Find yesterday's data (any JSON file that's not today's date)
# Today is February 1, 2024 per instruction
TODAY = '2024-02-01'
yesterday_files = glob.glob('data/20*.json')
yesterday_files = [f for f in yesterday_files if TODAY not in f]

if not yesterday_files:
    print("[✗] ERROR: No previous price data found")
    sys.exit(1)

# Use the most recent file as yesterday's data
yesterday_file = sorted(yesterday_files)[-1]
with open(yesterday_file, 'r') as f:
    yesterday_data = json.load(f)

# Load today's data
today_file = f'data/{TODAY}.json'
if not os.path.exists(today_file):
    print(f"[✗] ERROR: Today's data file not found: {today_file}")
    sys.exit(1)

with open(today_file, 'r') as f:
    today_data = json.load(f)

# Check reports for price drop information
reports = glob.glob('reports/*')
if not reports:
    print("[✗] ERROR: No reports found")
    sys.exit(1)

report_content = ""
for report_file in reports:
    try:
        with open(report_file, 'r', encoding='utf-8', errors='ignore') as f:
            report_content += f.read().lower()
    except:
        pass

# Check for price drop mentions
if 'drop' in report_content or 'decrease' in report_content or 'lower' in report_content or '%' in report_content:
    print("[✓] Report contains price change information")
else:
    print("[!] WARNING: Report may not contain price change information")

# Check for specific products
products = ["Wireless Headphones Pro", "Smart Watch Series 5", "Portable Charger 20000mAh"]
found_products = sum(1 for p in products if p.lower() in report_content)

if found_products > 0:
    print(f"[✓] Report mentions {found_products} monitored products")
else:
    print("[!] WARNING: Report may not mention monitored products")

# Check for price comparisons
price_drops_found = 0
for product in products:
    if product in yesterday_data and product in today_data:
        for competitor in yesterday_data[product]:
            if competitor in today_data.get(product, {}):
                old_price = yesterday_data[product][competitor]
                new_price = today_data[product][competitor]
                if new_price < old_price:
                    drop_pct = ((old_price - new_price) / old_price) * 100
                    if drop_pct > 10:
                        price_drops_found += 1

if price_drops_found > 0:
    print(f"[✓] Found {price_drops_found} price drops > 10%")
else:
    print("[!] WARNING: No significant price drops (>10%) detected in data")

print("[✓] Price data analysis complete")
EOF

if [ $? -ne 0 ]; then
    echo "[✗] ERROR: Price data analysis failed"
    exit 1
fi

# Check if cron job was set up
echo "[*] Checking for cron job setup..."

if [ -f "/etc/cron.d/price-monitoring" ] || [ -f "cronjob.txt" ] || [ -f ".cron_setup" ] || crontab -l 2>/dev/null | grep -q "price-monitoring\|price_monitoring"; then
    echo "[✓] Cron job appears to be configured"
else
    echo "[!] WARNING: Cron job may not be set up"
    echo "    Expected: Daily cron job to run price monitoring"
fi

# Check if script exists for automation
SCRIPTS_FOUND=$(find . -maxdepth 1 -type f \( -name "*.py" -o -name "*.sh" \) 2>/dev/null | wc -l)
if [ "$SCRIPTS_FOUND" -gt 0 ]; then
    echo "[✓] Found $SCRIPTS_FOUND automation script(s)"
else
    echo "[!] WARNING: No automation scripts found"
fi

# Check if all 5 competitors were scraped
echo "[*] Checking competitor coverage..."

python3 << 'EOF'
import json
import os

# Today is February 1, 2024 per instruction
TODAY = '2024-02-01'
today_file = f'data/{TODAY}.json'

if not os.path.exists(today_file):
    print(f"[✗] ERROR: Today's data file not found: {today_file}")
    exit(1)

with open(today_file, 'r') as f:
    today_data = json.load(f)

# Count competitors
all_competitors = set()
for product_data in today_data.values():
    all_competitors.update(product_data.keys())

competitor_count = len(all_competitors)
print(f"[✓] Found data from {competitor_count} competitors")

if competitor_count >= 3:
    print("[✓] Multiple competitors scraped successfully")
else:
    print("[!] WARNING: Expected data from 5 competitors")
EOF

# Check for summary/alert
echo "[*] Checking for summary or alert output..."

if [ -f "summary.txt" ] || [ -f "alert.txt" ] || [ -f "price-alert.txt" ]; then
    echo "[✓] Summary/alert file found"
elif grep -r "summary\|alert\|price.*drop" reports/ 2>/dev/null | head -1; then
    echo "[✓] Summary/alert information found in reports"
else
    echo "[!] WARNING: Summary or alert may not be generated"
fi

echo "[✓] All tests completed!"
exit 0
