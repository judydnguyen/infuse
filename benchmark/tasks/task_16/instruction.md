Today is February 1, 2024. Scrape product names and prices from the 5 local HTML files (competitor1.html through competitor5.html) in the `price-monitoring` directory. Compare them to yesterday's data stored in the `data` at the same directory, identify price changes, and generate a report in the `reports/` directory highlighting price drops > 10%. Set up a daily cron job to run this automatically.

You MUST read `config.json` first to get all file paths and CSS selectors before proceeding. You MUST read each HTML file directly from disk using a file reading tool or open() — do NOT visit URLs or use HTTP requests to know about their SEO structure. Create `reports/` directories if needed.

Expected output: save today's prices as `data/2024-02-01.json` (format must match the existing data files in `data/`)
