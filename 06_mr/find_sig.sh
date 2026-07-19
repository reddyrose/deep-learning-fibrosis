#!/bin/bash

# Filter associations with p-values less than 0.05/3000 (Bonferroni correction)
# Processes all files in the MR experiment directory

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."
INPUT_DIR="${BASE_DIR}/shriya/MR_experiment/completed_MR_2"
OUTPUT_FILE="${1:-significant_associations.txt}"
THRESHOLD="1.666667e-05"
THRESHOLD="1.041667e-06"

# Clear output file
> "$OUTPUT_FILE"

echo "Processing files in: $INPUT_DIR"
echo "Threshold: $THRESHOLD"
echo "Output: $OUTPUT_FILE"
echo

# Check directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Directory not found!"
    exit 1
fi

# Write header from first file
first_file=$(find "$INPUT_DIR" -type f -name "*.tsv" | head -n 1)
if [ -n "$first_file" ]; then
    head -n 1 "$first_file" > "$OUTPUT_FILE"
fi

total_files=0
total_significant=0

# Process each TSV file (excluding our output file)
for file in "$INPUT_DIR"/*.tsv; do
    [ ! -f "$file" ] && continue
    
    filename=$(basename "$file")
    
    # Skip if this is our output file
    [ "$filename" = "$(basename "$OUTPUT_FILE")" ] && continue
    
    echo "Processing: $filename"
    
    # Filter significant associations and count them
    significant=$(awk -v thresh="$THRESHOLD" 'NR>1 && $5+0 < thresh+0 {print; count++} END {print count > "/dev/stderr"}' "$file" 2>&1 1>> "$OUTPUT_FILE")
    
    total_files=$((total_files + 1))
    total_significant=$((total_significant + significant))
    
    echo "  Found: $significant significant associations"
done

echo
echo "Summary:"
echo "Files processed: $total_files"
echo "Total significant: $total_significant"
echo "Results in: $OUTPUT_FILE"
