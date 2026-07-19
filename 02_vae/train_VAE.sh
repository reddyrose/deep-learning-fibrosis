#!/usr/bin/bash
#SBATCH --job-name=UKBB_VAE_train
#SBATCH --time=20:00:00
#SBATCH --partition=euan
#SBATCH --gpus 1
#SBATCH --mem=100G  # Memory limit
#SBATCH --nodes=1 # Number of nodes
#SBATCH --ntasks=1 # Number of tasks

export TF_GPU_ALLOCATOR=cuda_malloc_async

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "${BASE_DIR}/shriya"

conda init
conda activate VAE

# This originally invoked train_vae_modified.py, which does not exist in this
# repository -- pointed at train_VAE_optimized.py (co-located in this folder,
# confirmed as the canonical training script) instead. Its "-ex" flag (an
# extra/excluded-images path) was dropped because train_VAE_optimized.py does
# not accept it.
python "${SCRIPT_DIR}/train_VAE_optimized.py" -i "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/SAM_masks" -o "${BASE_DIR}/shriya/VAE_rerun_trials/run_4" -qc "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium/mean_T1.csv" -b 32 -e 200 -ld 16


#python "${BASE_DIR}/shriya/train_VAE_optimized.py" -i "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/SAM_masks" -o "${BASE_DIR}/shriya/VAE_rerun_trials/run_1" -qc "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium/mean_T1.csv" -b 32 -e 200 -ld 16


#python "${BASE_DIR}/shriya/train_VAE_optimized.py" -i "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/SAM_masks" -o "${BASE_DIR}/shriya/VAE_rerun_trials/run_2" -qc "${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium/mean_T1.csv" -b 32 -e 200 -ld 16

