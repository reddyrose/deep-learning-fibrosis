#!/usr/bin/bash
#SBATCH --job-name=UKBB_VAE_train
#SBATCH --time=2:00:00
#SBATCH --partition=euan
#SBATCH --gpus 1
#SBATCH --mem=10G  # Memory limit
#SBATCH --nodes=1 # Number of nodes
#SBATCH --ntasks=1 # Number of tasks

python T1_percentiles_erroded.py