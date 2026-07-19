#!/bin/bash
#SBATCH --time=7-00:00:00
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --output=clump_%j.out
#SBATCH --error=clump_%j.err
#SBATCH --requeue
#SBATCH --mail-user=bgomes@stanford.edu

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1) Load bcftools
ml bcftools/1.16
ml plink/1.90b5.3

cd "${BASE_DIR}/shriya/SHMOLLI_hg38_converted_GWASs/T1_percentiles_10itr_eroded"

bash "${SCRIPT_DIR}/clumping_shriya.sh"
