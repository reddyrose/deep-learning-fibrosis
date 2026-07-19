#!/bin/bash

# Output file
OUTPUT="summary.txt"

# Write header
printf "%-65s %10s %10s %15s\n" "Phenotype" "h2" "SE" "p_value" > $OUTPUT
printf "%s\n" "------------------------------------------------------------------------------------------------------" >> $OUTPUT

# Loop through log files that don't contain "hematocrit"
for logfile in *.log; do
    # Skip files containing "hematocrit"
    if [[ $logfile == *"hematocrit"* ]]; then
        continue
    fi
    
    # Extract phenotype name
    phenotype=$(basename "$logfile" .sumstats.gz.log)
    
    # Extract h2 and SE from the log file
    line=$(grep "Total Observed scale h2:" "$logfile")
    
    if [[ -n "$line" ]]; then
        # Parse h2 and SE
        h2=$(echo "$line" | awk '{print $5}')
        se=$(echo "$line" | awk '{print $6}' | tr -d '()')
        
        # Calculate z-score and p-value using awk
        pvalue=$(awk -v h2="$h2" -v se="$se" 'BEGIN {
            z = h2 / se
            z = (z < 0) ? -z : z  # abs(z)
            # Approximate p-value using normal distribution
            # Using Abramowitz and Stegun approximation
            t = 1 / (1 + 0.2316419 * z)
            d = 0.3989423 * exp(-z * z / 2)
            prob = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
            pvalue = 2 * prob
            printf "%.2e", pvalue
        }')
        
        # Write to output file
        printf "%-65s %10.4f %10.4f %15s\n" "$phenotype" "$h2" "$se" "$pvalue" >> $OUTPUT
        
        # Also print to console
        printf "%-65s %10.4f %10.4f %15s\n" "$phenotype" "$h2" "$se" "$pvalue"
    fi
done

echo ""
echo "Summary written to $OUTPUT"
