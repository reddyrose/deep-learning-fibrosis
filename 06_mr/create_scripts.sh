#!/bin/bash

# Script to generate all 20 MR shell scripts

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# This value is baked into each generated child script below.
BASE_DIR="."

# Create T1_percentiles scripts (1-10)
for i in {1..10}; do
    filename="MR_T1_percentiles_extra_${i}.sh"

    cat > "$filename" << EOF
#!/bin/bash
#SBATCH --job-name=MR_T1_percentiles_extra_${i}
#SBATCH --output=MR_T1_percentiles_extra_${i}_%j.out
#SBATCH --error=MR_T1_percentiles_extra_${i}_%j.err
#SBATCH --cpus-per-task=8
#SBATCH --partition=euan
#SBATCH --time=7-00:00:00
#SBATCH --mem=16G
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=reddysh@stanford.edu

# Load R 4.4 on Sherlock
module load R/4.4

# BASE_DIR should point to the root data directory on your system
BASE_DIR="${BASE_DIR}"

# Run MR.R
Rscript \${BASE_DIR}/shriya/MR_experiment/MR_error_handling.R \\
  --protein_path=\${BASE_DIR}/shriya/ukb_ppp_processed/batch_${i}/cis_subsets_r2_001 \\
  --brain_path=\${BASE_DIR}/shriya/SHMOLLI_hg38_converted_GWASs/T1_percentiles_HHregressed \\
  --out_file=\${BASE_DIR}/shriya/MR_experiment/MR_T1_percentiles_extra_${i}.tsv
EOF

    chmod +x "$filename"
    echo "Created $filename"
done

# Create latent_dimensions scripts (1-10)
for i in {1..10}; do
    filename="MR_T1_latent_dimensions_extra_${i}.sh"

    cat > "$filename" << EOF
#!/bin/bash
#SBATCH --job-name=MR_T1_latent_dimensions_extra_${i}
#SBATCH --output=MR_T1_latent_dimensions_extra_${i}_%j.out
#SBATCH --error=MR_T1_latent_dimensions_extra_${i}_%j.err
#SBATCH --cpus-per-task=8
#SBATCH --partition=euan
#SBATCH --time=7-00:00:00
#SBATCH --mem=16G
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=reddysh@stanford.edu

# Load R 4.4 on Sherlock
module load R/4.4

# BASE_DIR should point to the root data directory on your system
BASE_DIR="${BASE_DIR}"

# Run MR.R
Rscript \${BASE_DIR}/shriya/MR_experiment/MR_error_handling.R \\
  --protein_path=\${BASE_DIR}/shriya/ukb_ppp_processed/batch_${i}/cis_subsets_r2_001 \\
  --brain_path=\${BASE_DIR}/shriya/SHMOLLI_hg38_converted_GWASs/latent_dimensions_HHregressed \\
  --out_file=\${BASE_DIR}/shriya/MR_experiment/MR_T1_latent_dimensions_extra_${i}.tsv
EOF

    chmod +x "$filename"
    echo "Created $filename"
done

echo "All 20 MR scripts have been created successfully!"
echo "Files created:"
echo "- MR_T1_percentiles_extra_1.sh through MR_T1_percentiles_extra_10.sh"
echo "- MR_T1_latent_dimensions_extra_1.sh through MR_T1_latent_dimensions_extra_10.sh"
