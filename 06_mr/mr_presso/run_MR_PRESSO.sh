#!/bin/bash
#SBATCH --job-name=mrpresso
#SBATCH --output=logs/mrpresso_%A_%a.out
#SBATCH --error=logs/mrpresso_%A_%a.err
#SBATCH --time=7-00:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --array=1-20
#SBATCH --partition=euan

# Load modules
ml system
ml R/4.4.2
ml curl/8.17.0
ml openssl/3.6.0

# Create logs directory if it doesn't exist
mkdir -p logs

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."

# Fixed bug: this array was declared 1-37 while PAIRS_FILE below
# (mrpresso_pairs_2.txt) has only 20 rows, so tasks 21-37 would have read past
# the end of the file and failed. Array size now matches the 20-row file.
# mrpresso_pairs.txt (37 rows) is kept alongside as the other candidate
# manifest -- confirm which pair list the reported run actually used; if it
# was mrpresso_pairs.txt, change PAIRS_FILE below and set --array=1-37.
# Set paths
PROTEIN_DIR="${BASE_DIR}/shriya/CAUSE_gwas_summary_stats/cis_pqtls_gwas"
OUTCOME_DIR="${BASE_DIR}/shriya/CAUSE_gwas_summary_stats"
PAIRS_FILE="mrpresso_pairs_2.txt"
R_SCRIPT="run_MR_PRESSO.R"

# Get the protein and outcome for this array task
PROTEIN=$(sed -n "${SLURM_ARRAY_TASK_ID}p" $PAIRS_FILE | awk '{print $1}')
OUTCOME=$(sed -n "${SLURM_ARRAY_TASK_ID}p" $PAIRS_FILE | awk '{print $2}')

echo "========================================="
echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Array Task ID: ${SLURM_ARRAY_TASK_ID}"
echo "Protein: ${PROTEIN}"
echo "Outcome: ${OUTCOME}"
echo "Started: $(date)"
echo "========================================="

# Run the R script
Rscript $R_SCRIPT $PROTEIN $OUTCOME $PROTEIN_DIR $OUTCOME_DIR

echo "========================================="
echo "Finished: $(date)"
echo "========================================="


