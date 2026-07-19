import os
import itertools
import pandas as pd
import re

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# LDSC_DIR should point to the LDSC installation (munge_sumstats.py, ldsc.py).
# LD_REF_DIR should point to your LD reference panel (e.g. eur_w_ld_chr).
BASE_DIR = "."
LDSC_DIR = "."
LD_REF_DIR = "."

# Define base output directory
output_base = os.path.join(BASE_DIR, "shriya/ldsc")

# Define category folders
categories = ["GWAS_results", "VAE_GWAS"]
for category in categories:
    munge_path = os.path.join(output_base, "munge_statistics", category)
    h2_path = os.path.join(output_base, "h2", category)
    rg_path = os.path.join(output_base, "rg", category)

    if not os.path.exists(munge_path):
        os.makedirs(munge_path)
 
    if not os.path.exists(h2_path):
        os.makedirs(h2_path)

    if not os.path.exists(rg_path):
        os.makedirs(rg_path)

# Create additional rg folder for between-category correlations
rg_between_path = os.path.join(output_base, "rg", "GWAS_VAE_cross")
if not os.path.exists(rg_between_path):
    os.makedirs(rg_between_path)

# Define GWAS lists
gwas_results_list = []
vae_gwas_list = []

# Define paths
paths = {
    "GWAS_results": os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/GWAS_results"),
    "VAE_GWAS": os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/VAE_GWAS")
}

# Populate lists
gwas_dict = {
    "GWAS_results": gwas_results_list,
    "VAE_GWAS": vae_gwas_list
}

for category, path in paths.items():
    for i in os.listdir(path):
        x = os.path.join(path, i)
        if i.endswith(".glm.linear"):
            gwas_dict[category].append(x)

print("Found {} files in GWAS_results".format(len(gwas_results_list)))
print("Found {} files in VAE_GWAS".format(len(vae_gwas_list)))

# **Munge Statistics & h2 Calculation**
all_phenotypes = []  # Track all phenotypes for rg calculation

for category, gwas_list in gwas_dict.items():
    for i in gwas_list:
        x = i.split('/')[-1]  # Get filename
        match = re.search(r"\.(.*?)\.glm\.linear", x)
        if match:
            y = match.group(1)  # Extract the phenotype name
        else:
            # If pattern doesn't match, use full filename without extension
            y = x.replace('.glm.linear', '')

        print('Processing file: {} (category: {})'.format(y, category))

        df = pd.read_csv(i, sep='\t', header=0, low_memory=False)
        N_column = int(df['OBS_CT'].iloc[0])

        # Compute Z-score
        df['Z'] = df['BETA'] / df['SE']

        # Define output paths
        output_munge = os.path.join(output_base, "munge_statistics", category, y)
        output_h2 = os.path.join(output_base, "h2", category, y)

        # Save transformed GWAS file
        ldsc_input_dir = os.path.join(output_base, "ldsc_input")
        if not os.path.exists(ldsc_input_dir):
            os.makedirs(ldsc_input_dir)
        df_path = os.path.join(ldsc_input_dir, "{}.glm.linear".format(y))
        df.to_csv(df_path, sep='\t', index=False)

        # Run Munge Sumstats
        os.system('{}/munge_sumstats.py --sumstats {} --out {} --merge-alleles {}/w_hm3.snplist --chunksize 500000 --N {} --ignore T_STAT,BETA,SE'.format(LDSC_DIR, df_path, output_munge, LD_REF_DIR, N_column))

        # Run h2 Calculation
        os.system('{}/ldsc.py --h2 {}.sumstats.gz --ref-ld-chr {} --w-ld-chr {} --out {}.sumstats.gz'.format(LDSC_DIR, output_munge, LD_REF_DIR, LD_REF_DIR, output_h2))
        
        # Store phenotype info for rg calculation
        all_phenotypes.append((category, y, i))

print("\nTotal phenotypes processed: {}".format(len(all_phenotypes)))

# **Calculate rg (Genetic Correlation) for ALL pairwise combinations**
print("\n=== Starting genetic correlation calculations ===")

# Generate all pairwise combinations (avoiding duplicates and self-comparisons)
pairwise_combinations = []
for idx1, (cat1, pheno1, path1) in enumerate(all_phenotypes):
    for idx2, (cat2, pheno2, path2) in enumerate(all_phenotypes):
        if idx1 < idx2:  # Avoid duplicates and self-comparisons
            pairwise_combinations.append(((cat1, pheno1), (cat2, pheno2)))

print("Total genetic correlations to calculate: {}".format(len(pairwise_combinations)))

for (cat1, pheno1), (cat2, pheno2) in pairwise_combinations:
    # Determine output folder based on whether it's within-category or between-category
    if cat1 == cat2:
        # Within same category
        output_rg = os.path.join(output_base, "rg", cat1, "{}-{}".format(pheno1, pheno2))
    else:
        # Between categories
        output_rg = os.path.join(output_base, "rg", "GWAS_VAE_cross", "{}-{}".format(pheno1, pheno2))

    print("Calculating rg: {} <-> {}".format(pheno1, pheno2))

    # Run Genetic Correlation analysis
    os.system('{}/ldsc.py --rg {}/munge_statistics/{}/{}.sumstats.gz,{}/munge_statistics/{}/{}.sumstats.gz --ref-ld-chr {} --w-ld-chr {} --out {}'.format(LDSC_DIR, output_base, cat1, pheno1, output_base, cat2, pheno2, LD_REF_DIR, LD_REF_DIR, output_rg))

print("\n=== Analysis complete! ===")
