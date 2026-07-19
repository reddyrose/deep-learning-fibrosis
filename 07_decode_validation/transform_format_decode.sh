#!/bin/bash

echo "Converting all .txt files to *_merged.txt.gz format..."

for input in *.txt; do
  # Skip if no .txt files found
  [[ ! -e "$input" ]] && { echo "No .txt files found"; break; }
  
  # Create output filename: replace .txt with _merged.txt.gz
  output="${input%.txt}_merged.txt.gz"
  
  # Skip if output already exists
  if [[ -e "$output" ]]; then
    echo "[SKIP] $output already exists"
    continue
  fi
  
  echo "[INFO] Converting $input => $output"
  
  awk 'BEGIN {OFS="\t"}
  NR==1 {
    # Print new header
    print "CHROM", "GENPOS", "ID", "ALLELE0", "ALLELE1", "A1FREQ", "INFO", "N", "TEST", "BETA", "SE", "CHISQ", "LOG10P", "EXTRA"
    next
  }
  {
    # Parse input columns
    chrom = $1
    pos = $2
    name = $3
    rsids = $4
    effectAllele = $5
    otherAllele = $6
    beta = $7
    pval = $8
    log10p = $9
    se = $10
    n = $11
    maf = $12
    
    # Remove "chr" prefix from chrom
    gsub(/^chr/, "", chrom)
    
    # Create ID: remove "chr" from name and add ":imp:v1"
    id = name
    gsub(/^chr/, "", id)
    id = id ":imp:v1"
    
    # Calculate CHISQ = (BETA/SE)^2
    chisq = (beta/se)^2
    
    # Set INFO to 1.0
    info = 1.0
    
    # Set TEST to ADD
    test = "ADD"
    
    # Set EXTRA to NA
    extra = "NA"
    
    # Print output in new format
    print chrom, pos, id, effectAllele, otherAllele, maf, info, n, test, beta, se, chisq, log10p, extra
  }' "$input" | gzip > "$output"
  
  echo "[DONE] Created $output"
done

echo ""
echo "All conversions complete!"
