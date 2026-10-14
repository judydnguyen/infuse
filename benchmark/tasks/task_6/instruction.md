Write a Python program that reads all CSV files in the current directory, merges them using their shared column(s), and writes the merged result to a new CSV file.

Start by reading `data1.csv`, `data2.csv`, and `data3.csv` in full to understand their schemas and identify shared columns before writing the program.

You must:
- Automatically discover all CSV files in the current directory
- Identify the column(s) common to all CSV files and use them as join keys
- Perform a deterministic join (do not rely on file order unless specified)
- Write the merged result to a single output CSV file