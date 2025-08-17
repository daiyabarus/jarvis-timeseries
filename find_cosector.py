import pandas as pd
import sys

# Check if CSV file is provided as argument
if len(sys.argv) != 2:
    print("Usage: python script.py input.csv")
    sys.exit(1)

# Read the input CSV file
input_file = sys.argv[1]
try:
    df = pd.read_csv(input_file)
except FileNotFoundError:
    print(f"Error: File {input_file} not found")
    sys.exit(1)
except Exception as e:
    print(f"Error reading CSV: {e}")
    sys.exit(1)

# Group by Latitude, Longitude, and Dir to find matching Cellnames
grouped = df.groupby(['Latitude', 'Longitude', 'Dir'])

# Initialize result DataFrame
result = []

# Process each group
for _, group in grouped:
    cellnames = group['Cellname'].tolist()
    if len(cellnames) == 2:
        # If exactly two Cellnames share the same Latitude, Longitude, and Dir
        result.append({'Cellname': cellnames[0], 'CoSector': cellnames[1]})
        result.append({'Cellname': cellnames[1], 'CoSector': cellnames[0]})
    else:
        # If only one or more than two Cellnames, mark as "No cosector"
        for cellname in cellnames:
            result.append({'Cellname': cellname, 'CoSector': 'No cosector'})

# Convert to DataFrame
output_df = pd.DataFrame(result)

# Sort by Cellname to ensure consistent output order
output_df = output_df.sort_values(by='Cellname').reset_index(drop=True)

# Save to output CSV
output_file = 'cosector_output.csv'
output_df.to_csv(output_file, index=False)
print(f"Output saved to {output_file}")