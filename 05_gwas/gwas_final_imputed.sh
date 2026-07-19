#!/bin/bash
#SBATCH --time=48:00:00
#SBATCH --partition=euan
#SBATCH --mail-type=BEGIN,END,FAIL,
#SBATCH --mail-user=reddysh@stanford.edu
#SBATCH --cpus-per-task=1
#SBATCH --mem=64G
#SBATCH --output=gwas_t1_%j.out
#SBATCH --error=gwas_t1_%j.err
#SBATCH --requeue

# UKBB ID for imputed data: ukb22282

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# UKBB_DIR should point to the UK Biobank raw genetic data root (requires
# approved UK Biobank access, application 22282).
BASE_DIR="."
UKBB_DIR="."

ml biology
ml plink/2.0a2
cd "${BASE_DIR}/shriya/"

plink2 --bfile "${UKBB_DIR}/24983/array_imp_combined/pgen/ukb24983_cal_hla_cnv_imp" --keep "${BASE_DIR}/bruna/euro_minus_first/euro_minus_exclusion_minus_firstdegree_imputed.txt" --maf 0.01 --mac 20 --geno 0.1 --hwe 1e-15 --mind 0.1 --double-id --pheno "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/cleaned_T1_percentiles_HHregressed_imputed.no_outliers.residuals.qnorm.txt" --input-missing-phenotype -1000.0 --adjust --glm --out SHMOLLI-output-unet-myocardium-update2/GWAS_output