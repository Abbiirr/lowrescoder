# Task: Convert CSV to Parquet

## Objective

Write a Python script that converts `data.csv` to Parquet format.

## Requirements

1. Edit `convert.py` to read `data.csv` and write it to `output.parquet`.
2. The output file must be valid Parquet format.
3. All 25 rows from the CSV must be present in the Parquet file.
4. All columns (`id`, `name`, `age`, `city`, `salary`) must be preserved.
5. The script must be runnable with `python convert.py`.
6. You may use `pandas` and `pyarrow` (both are available).

## Files

- `data.csv` — the input CSV file (25 rows, 5 columns)
- `convert.py` — the script you must edit
- `output.parquet` — the expected output file (created by your script)
