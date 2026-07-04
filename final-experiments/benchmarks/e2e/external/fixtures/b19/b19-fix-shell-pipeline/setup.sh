#!/usr/bin/env bash
set -euo pipefail

# Create input CSV data
cat > data.csv << 'CSV'
name,email,status
Charlie,charlie@example.com,active
Alice,alice@example.com,active
Dave,dave@example.com,inactive
Bob,bob@example.com,active
Eve,eve@example.com,inactive
Frank,frank@example.com,active
CSV

# Create the expected output for verification
cat > expected.json << 'JSON'
[
  {"name": "Alice", "email": "alice@example.com", "status": "active"},
  {"name": "Bob", "email": "bob@example.com", "status": "active"},
  {"name": "Charlie", "email": "charlie@example.com", "status": "active"},
  {"name": "Frank", "email": "frank@example.com", "status": "active"}
]
JSON

# Create the broken pipeline script
cat > pipeline.sh << 'SCRIPT'
#!/usr/bin/env bash
# Data pipeline: CSV -> filter -> sort -> JSON

INPUT="data.csv"
OUTPUT="output.json"

# Step 1: Filter rows where status is "active" (skip header)
# BUG: -P flag is unnecessary and pattern is wrong (uses ^ anchor with .* which
#       matches everything, then checks for "active$" but the CSV has no trailing space)
# BUG: The pattern "^.*,active$" would work, but the actual bug is using -P and
#       the pattern "^.*,\s*active\s*$" which can behave differently across systems
FILTERED=$(tail -n +2 "$INPUT" | grep -P "^.*,\s+active\s*$")

# Step 2: Sort by name (first column)
# BUG: Sort step is completely missing — FILTERED is used directly without sorting

# Step 3: Convert to JSON with awk
# BUG: awk uses default field separator (space) instead of comma
echo "[" > "$OUTPUT"
LINES=$(echo "$FILTERED" | wc -l)
COUNT=0
echo "$FILTERED" | awk '{
    COUNT++
    name=$1
    email=$2
    status=$3
    if (COUNT < LINES) {
        printf "  {\"name\": \"%s\", \"email\": \"%s\", \"status\": \"%s\"},\n", name, email, status
    } else {
        printf "  {\"name\": \"%s\", \"email\": \"%s\", \"status\": \"%s\"}\n", name, email, status
    }
}' LINES="$LINES" >> "$OUTPUT"
echo "]" >> "$OUTPUT"

echo "Pipeline complete. Output written to $OUTPUT"
SCRIPT
chmod +x pipeline.sh

echo "Setup complete. pipeline.sh has 3 bugs to fix."
