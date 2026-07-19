#!/usr/bin/bash
#SBATCH --job-name=UKBB_SHMOLLI_deploy
#SBATCH --time=9:00:00
#SBATCH --partition=euan
#SBATCH --gpus 1
#SBATCH --mem=6G  # Memory limit
#SBATCH --nodes=1 # Number of nodes
#SBATCH --ntasks=1 # Number of tasks
#SBATCH --partition=euan              # Specify the GPU partition (if necessary)

conda init
conda activate VAE

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python "${SCRIPT_DIR}/deploy_VAE_reconstruction.py" -mw "${BASE_DIR}/shriya/VAE_rerun_trials/run_3/cvae_16d_best.weights.h5" -i "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/SAM_masks" -o "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/SHMOLLI_VAE_16_output" -d 16



#python "${SCRIPT_DIR}/deploy_VAE_reconstruction.py" -mw "${BASE_DIR}/shriya/VAE_rerun_trials/run_1/cvae_16d_optimized.weights.h5" -i "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/SAM_masks" -o "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/SHMOLLI_VAE_16_output" -d 16

#python "${SCRIPT_DIR}/deploy_VAE_reconstruction.py" -mw "${BASE_DIR}/shriya/SHMOLLI-VAE-output/cvae_16d_optimized.weights.h5" -i "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium/SAM_masks" -o "${BASE_DIR}/shriya/SHMOLLI_VAE_16_output" -d 16
