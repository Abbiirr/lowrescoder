#!/usr/bin/env bash
# Setup for tb-004-csv-to-parquet
# Creates a CSV file and an empty Python conversion script.
set -euo pipefail

# Ensure parquet dependencies are available inside the benchmark container.
python -m pip install --quiet pandas pyarrow

# Create sample CSV with 100 rows
cat > data.csv << 'CSV'
id,name,age,city,salary
1,Alice,30,New York,75000.50
2,Bob,25,San Francisco,82000.00
3,Charlie,35,Chicago,68000.75
4,Diana,28,Boston,71000.25
5,Eve,32,Seattle,90000.00
6,Frank,45,Denver,65000.50
7,Grace,29,Austin,78000.00
8,Henry,38,Portland,72000.25
9,Iris,26,Miami,69000.75
10,Jack,33,Atlanta,76000.50
11,Kate,41,Dallas,84000.00
12,Leo,27,Phoenix,67000.25
13,Mia,36,Detroit,73000.75
14,Noah,31,Minneapolis,80000.50
15,Olivia,24,Nashville,66000.00
16,Paul,39,Charlotte,77000.25
17,Quinn,34,Columbus,71000.75
18,Rose,42,Indianapolis,85000.50
19,Sam,29,San Diego,79000.00
20,Tina,37,Philadelphia,74000.25
21,Uma,26,Houston,68000.75
22,Vince,43,Washington,88000.50
23,Wendy,30,Baltimore,70000.00
24,Xander,35,Milwaukee,76000.25
25,Yuki,28,Sacramento,82000.75
CSV

# Create empty conversion script
cat > convert.py << 'STUB'
#!/usr/bin/env python3
"""Convert data.csv to output.parquet.

Requirements:
- Read data.csv
- Write to output.parquet in Parquet format
- Preserve all columns and data types
"""
# TODO: Implement conversion
STUB

chmod +x convert.py

echo "Setup complete. data.csv created with 25 rows and parquet deps installed."
