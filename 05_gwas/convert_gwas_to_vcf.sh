#!/usr/bin/env bash

# =====================
# 1)Input file
# =====================
# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# HTSLIB_BIN should point to the directory containing bgzip/tabix; leave as ""
# to use whichever bgzip/tabix are found on your PATH.
BASE_DIR="."
HTSLIB_BIN=""

# Change this to the path of your GWAS summary file
GWAS_FILE="${BASE_DIR}/shriya/kgwas_outputs/gwas_inputs_formatted/Mean_T1_myocardium_formatted_gwas.txt"

# =====================
# 2) Create VCF header
# =====================
cat <<EOF > header.txt
##fileformat=VCFv4.2
##INFO=<ID=A1,Number=1,Type=String,Description="Allele used to estimate effect in original GWAS">
##INFO=<ID=TEST,Number=1,Type=String,Description="Statistical model (e.g., ADD)">
##INFO=<ID=N,Number=1,Type=Integer,Description="Sample size for this variant">
##INFO=<ID=BETA,Number=1,Type=Float,Description="Effect size estimate from GWAS">
##INFO=<ID=SE,Number=1,Type=Float,Description="Standard error of the effect size estimate">
##INFO=<ID=T_STAT,Number=1,Type=Float,Description="T-statistic of the effect">
##INFO=<ID=P,Number=1,Type=Float,Description="P-value of the association">
#CHROM  POS     ID      REF     ALT     QUAL    FILTER  INFO
EOF

# =============================================================================
# 3) Convert GWAS summary rows into VCF records (skip header row with NR>1)
# =============================================================================
awk 'NR>1 {
  # $1=#CHROM, $2=POS, $3=SNP, $4=REF, $5=ALT, $6=A1, $7=TEST, $8=N, $9=BETA, $10=SE, $11=T_STAT, $12=P
  # We place columns into the VCF fields as follows:
  # CHROM -> $1
  # POS   -> $2
  # ID    -> $3 (SNP name, e.g., "1:753405:C:A")
  # REF   -> $4
  # ALT   -> $5
  # QUAL  -> "."
  # FILTER-> "."
  # INFO  -> store the remaining columns as key=value pairs
  printf "%s\t%s\t%s\t%s\t%s\t.\t.\tA1=%s;TEST=%s;N=%s;BETA=%s;SE=%s;T_STAT=%s;P=%s\n",
         $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
}' "${GWAS_FILE}" > body.txt

# =========================================
# 4) Combine header + body into one VCF
# =========================================
cat header.txt body.txt > mygwas.vcf

# =============================
# 5) bgzip and index the VCF
# =============================
BGZIP="bgzip"
TABIX="tabix"
if [ -n "$HTSLIB_BIN" ]; then
    BGZIP="${HTSLIB_BIN}/bgzip"
    TABIX="${HTSLIB_BIN}/tabix"
fi
"$BGZIP" mygwas.vcf
"$TABIX" -p vcf mygwas.vcf.gz

# =============
# 6) Clean up
# =============
rm header.txt body.txt

echo "Done! Created mygwas.vcf.gz (compressed + indexed)."
