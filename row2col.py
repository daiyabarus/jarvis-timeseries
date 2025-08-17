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

# Group by Cellname_Source and sort by Distance (KM) to get top 5
grouped = df.groupby('Cellname_Source').apply(
    lambda x: x.nsmallest(5, 'Distance (KM)')[['Cellname_Target', 'Distance (KM)']]
).reset_index()

# Pivot to create columns for 1st to 5th closest targets and their distances
result = []
for name, group in grouped.groupby('Cellname_Source'):
    row = {'Cellname': name}
    for i, (_, data) in enumerate(group.iterrows(), 1):
        if i > 5:  # Ensure only top 5 are considered
            break
        row[f'{i}th'] = data['Cellname_Target']
        row[f'Distance{i}'] = data['Distance (KM)']
    result.append(row)

# Convert to DataFrame
output_df = pd.DataFrame(result)

# Fill missing columns with NaN if any group has fewer than 5 targets
expected_columns = ['Cellname', '1st', 'Distance1', '2nd', 'Distance2', '3th', 'Distance3', 
                   '4th', 'Distance4', '5th', 'Distance5']
for col in expected_columns:
    if col not in output_df.columns:
        output_df[col] = pd.NA

# Reorder columns to match expected output
output_df = output_df[expected_columns]

# Save to output CSV
output_file = 'output.csv'
output_df.to_csv(output_file, index=False)
print(f"Output saved to {output_file}")