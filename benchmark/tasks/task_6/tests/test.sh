#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running CSV merge tests..."

# Find the output CSV file (any CSV that's not one of the input files)
input_files=("data1.csv" "data2.csv" "data3.csv")
output_file=""

for csv_file in *.csv; do
    if [ ! -f "$csv_file" ]; then
        continue
    fi
    
    # Check if this file is not one of the input files
    is_input=false
    for input_file in "${input_files[@]}"; do
        if [ "$csv_file" = "$input_file" ]; then
            is_input=true
            break
        fi
    done
    
    if [ "$is_input" = false ]; then
        output_file="$csv_file"
        break
    fi
done

# Check if output file was found
if [ -z "$output_file" ] || [ ! -f "$output_file" ]; then
    echo "[✗] ERROR: No output CSV file found (expected a new CSV file that is not data1.csv, data2.csv, or data3.csv)"
    exit 1
fi

echo "[✓] Found output file: $output_file"

# Check if merged file has correct structure
# Should have columns: id, name, age, department, salary, location, start_date
expected_columns="id,name,age,department,salary,location,start_date"

# Read first line and check columns
header=$(head -n 1 "$output_file" | tr -d '\r\n')
if [ "$header" != "$expected_columns" ]; then
    echo "[✗] ERROR: Merged file has incorrect columns"
    echo "  Expected: $expected_columns"
    echo "  Got: $header"
    exit 1
fi

echo "[✓] Merged file has correct columns"

# Check if merged file has correct number of rows (should have 3 data rows + 1 header)
row_count=$(wc -l < "$output_file")
if [ "$row_count" -ne 4 ]; then
    echo "[✗] ERROR: Merged file has incorrect number of rows"
    echo "  Expected: 4 (1 header + 3 data rows)"
    echo "  Got: $row_count"
    exit 1
fi

echo "[✓] Merged file has correct number of rows"

# Check if all IDs are present (1, 2, 3)
for id in 1 2 3; do
    if ! grep -q "^$id," "$output_file"; then
        echo "[✗] ERROR: ID $id not found in merged output"
        exit 1
    fi
done

echo "[✓] All expected IDs found in merged output"

# Check if data from all files is present
# Check for name (from data1.csv)
if ! grep -q "Alice\|Bob\|Charlie" "$output_file"; then
    echo "[✗] ERROR: Name data from data1.csv not found"
    exit 1
fi

# Check for department (from data2.csv)
if ! grep -q "Engineering\|Marketing\|Sales" "$output_file"; then
    echo "[✗] ERROR: Department data from data2.csv not found"
    exit 1
fi

# Check for location (from data3.csv)
if ! grep -q "New York\|San Francisco\|Seattle" "$output_file"; then
    echo "[✗] ERROR: Location data from data3.csv not found"
    exit 1
fi

echo "[✓] Data from all source files is present in merged output"

echo "[✓] All tests passed!"
exit 0
