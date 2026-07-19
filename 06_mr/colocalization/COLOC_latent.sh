#!/bin/bash
#SBATCH --job-name=COLOC
#SBATCH --output=COLOC_T1_%j.out
#SBATCH --error=COLOC_T1_%j.err
#SBATCH --partition=euan
#SBATCH --time=48:00:00
#SBATCH --mem=64G
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=reddysh@stanford.edu

# Load R 4.4 on Sherlock
module load R/4.4

# Directory containing this script (i.e. colocalization/ in the repo)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run COLOC_latent.R (co-located in this folder)
Rscript "${SCRIPT_DIR}/COLOC_latent.R"
