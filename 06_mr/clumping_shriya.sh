#!/usr/bin/env bash
set -e  # Exit on first error

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."

# Move into the folder with your *_gwas_rsids.txt files
#cd "${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar"

# Reference data prefix for PLINK
LD_BFILE="${BASE_DIR}/bruna/1000G/all_hg38_nodup"

# Loop over all files ending in "_gwas_rsids.txt"
for f in *_gwas.txt; do

  # If none found, break
  [[ "$f" == "*_gwas.txt" || ! -e "$f" ]] && { echo "No *_gwas.txt files found."; break; }

  # Strip off "_gwas_rsids.txt" to form the output prefix
  prefix="${f%_gwas.txt}"

  echo "[INFO] Clumping $f => output prefix '$prefix'"

  # Run PLINK clumping
  plink --bfile "$LD_BFILE" \
    --chr 1-22 \
    --allow-extra-chr \
    --clump "$f" \
    --clump-snp-field SNP \
    --clump-field P \
    --out "r2_001/${prefix}" \
    --clump-kb 100 \
    --clump-p1 5e-5 \
    --clump-p2 1e-3 \
    --clump-r2 0.01 \
    --allow-no-sex

  echo "[DONE] Created $prefix.clumped"

done

echo "All clumping tasks done!"

