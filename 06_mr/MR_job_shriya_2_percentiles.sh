#!/bin/bash
#SBATCH --partition=euan
#SBATCH --job-name=pqtl_MR_T1
#SBATCH --cpus-per-task=8          # matches R workers
#SBATCH --mem=64G
#SBATCH --time=7-00:00:00
#SBATCH --output=MR_%j.out
#SBATCH --error=MR_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=bgomes@stanford.edu

# ── 1. Load R 4.4 on Sherlock ──────────────────────────────────────────
module load R/4.4

# ── 2. Keep every R session single‑threaded (no oversubscription) ──────
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 3. Run the MR script on ALL protein folders in one go ──────────────
Rscript "${SCRIPT_DIR}/MR_shriya_2.R" \
  --protein_roots="${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_01/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_02/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_03/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_04/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_05/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_06/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_07/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_08/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_09/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_4/job_10/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_3/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar_2/cis_subsets_r2_001,\
${BASE_DIR}/bruna/vcf_gwas_pa/protein_example/out_tar/cis_subsets_r2_001" \
  --brain_path="${BASE_DIR}/shriya/SHMOLLI_hg38_converted_GWASs/T1_percentiles" \
  --out_file="${BASE_DIR}/bruna/vcf_gwas_pa/MR_experiment/cis_scripts/shriya_T1/MR_T1_percentiles.tsv"

