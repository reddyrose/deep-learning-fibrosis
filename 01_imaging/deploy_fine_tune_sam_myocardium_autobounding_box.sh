#!/usr/bin/bash
#SBATCH --job-name=UKBB_SHMOLLI_deploy
#SBATCH --time=48:00:00
#SBATCH --partition=euan
#SBATCH --gpus 1
#SBATCH --mem=100G # Memory limit
#SBATCH --nodes=1 # Number of nodes
#SBATCH --ntasks=1 # Number of tasks

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# HF_TOKEN should be set to your own Hugging Face access token (do not hardcode
# tokens in scripts committed to version control); e.g. `export HF_TOKEN=...`
# before running this script.
BASE_DIR="."

python fine_tune_sam_myocardium_autobounding_box.py -t "${HF_TOKEN}" -uw "${BASE_DIR}/shriya/myocardium-unet-256.h5" -n "reddysh/finetuned-myocardium-medSAM" -i "${BASE_DIR}/shriya/UKBB_SHMOLLI-pngimages" -o "${BASE_DIR}/shriya/SHMOLLI-output-2" &

wait
