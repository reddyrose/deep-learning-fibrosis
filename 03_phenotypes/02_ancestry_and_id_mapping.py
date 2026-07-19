"""
Remaps UK Biobank application-22282 patient IDs to application-24983 IDs
(the ID space used by the imputed genotype files) for the T1 phenotype
residuals and the European-ancestry sample-inclusion list.

The European-ancestry output of this script, euro_minus_exclusion_minus_firstdegree_imputed.txt,
is the --keep sample list read directly by 05_gwas/gwas_final_imputed.sh and
05_gwas/gwas_VAE.sh -- despite being labelled "Legacy Code" in the original
notebook, it is live, load-bearing production code, not dead exploration.

Split out of the original 03_phenotypes/01_SMHOLLI_tranformer_phenotype_associations.ipynb
during repository cleanup -- see docs/REVIEW_REQUIRED.md.
"""

import os

import pandas as pd

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR = "."

patient_mapping = pd.read_table(
    os.path.join(BASE_DIR, "shriya/ukb22282_24983_mapping.tsv"), header=None
)


def get_mapped_ID(id_to_find, mapping_df):
    """Look up the column-0 (application 24983) ID for a given column-1 (application 22282) ID."""
    if id_to_find in mapping_df[1].values:
        row_index = mapping_df[mapping_df[1] == id_to_find].index[0]
        return mapping_df.loc[row_index, 0]
    return None


def reverse_mapped_ID(id_to_find, mapping_df):
    """Look up the column-1 (application 22282) ID for a given column-0 (application 24983) ID."""
    if id_to_find in mapping_df[0].values:
        row_index = mapping_df[mapping_df[0] == id_to_find].index[0]
        return int(mapping_df.loc[row_index, 1])
    return None


# ---------------------------------------------------------------------------
# Remap T1 phenotype residuals to application-24983 IDs.
# ---------------------------------------------------------------------------

imputed_residuals = pd.read_csv(
    os.path.join(
        BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/T1_phenotypes.no_outliers.residuals.qnorm.txt"
    ),
    sep="\t",
)

for index, row in imputed_residuals.iterrows():
    mapped_IID = reverse_mapped_ID(int(row["IID"]), patient_mapping)
    imputed_residuals.at[index, "IID"] = mapped_IID
    imputed_residuals.at[index, "FID"] = mapped_IID

imputed_residuals = imputed_residuals.dropna(subset=["IID"])
imputed_residuals["IID"] = imputed_residuals["IID"].astype(int)
imputed_residuals["FID"] = imputed_residuals["FID"].astype(int)
imputed_residuals = imputed_residuals.dropna()

t1_imputed_path = os.path.join(
    BASE_DIR,
    "shriya/SHMOLLI-output-unet-myocardium/T1_phenotypes_imputed.no_outliers.residuals.qnorm.txt",
)
imputed_residuals.to_csv(t1_imputed_path, sep="\t", index=False)
print(f"Saved: {t1_imputed_path}")

# ---------------------------------------------------------------------------
# Remap the European-ancestry (minus 3rd-degree-relative exclusions) sample
# list. This is the --keep file for 05_gwas/gwas_final_imputed.sh and
# 05_gwas/gwas_VAE.sh.
# ---------------------------------------------------------------------------

european_ancestry = pd.read_csv(
    os.path.join(BASE_DIR, "bruna/euro_minus_first/euro_minus_exclusion_minus_firstdegree.txt"),
    sep="\t",
    header=None,
)
european_ancestry = european_ancestry.dropna()

for index, row in european_ancestry.iterrows():
    mapped_IID = reverse_mapped_ID(int(row[0]), patient_mapping)
    european_ancestry.at[index, 0] = mapped_IID
    european_ancestry.at[index, 1] = mapped_IID

euro_imputed_path = os.path.join(
    BASE_DIR, "bruna/euro_minus_first/euro_minus_exclusion_minus_firstdegree_imputed.txt"
)
european_ancestry.to_csv(euro_imputed_path, sep="\t", index=False)
print(f"Saved: {euro_imputed_path}")
