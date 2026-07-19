"""
Prepares per-phenotype-group covariate tables (VAE latent dimensions, plus
one per disease group from 03_disease_status_annotation.py) for downstream
regression, and remaps a couple of residual-phenotype files to
application-24983 IDs.

Split out of the original 03_phenotypes/01_SMHOLLI_tranformer_phenotype_associations.ipynb
during repository cleanup -- see docs/REVIEW_REQUIRED.md.
"""

import os

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR = "."

# ---------------------------------------------------------------------------
# Re-derive the per-disease myocardium subsets written by
# 03_disease_status_annotation.py (that script doesn't persist them
# individually, only the combined mean_T1.csv with status columns).
# ---------------------------------------------------------------------------

unet_myocardium_data = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/mean_T1.csv")
)

HCM_myocardium_data = unet_myocardium_data[
    (unet_myocardium_data["HCM_status"] == True) & (unet_myocardium_data["quality_controlled"] == True)
]
DCM_myocardium_data = unet_myocardium_data[
    (unet_myocardium_data["DCM_status"] == True) & (unet_myocardium_data["quality_controlled"] == True)
]
valvular_myocardium_data = unet_myocardium_data[
    (unet_myocardium_data["valvular_status"] == True) & (unet_myocardium_data["quality_controlled"] == True)
]
amyloidosis_myocardium_data = unet_myocardium_data[
    (unet_myocardium_data["amyloidosis_status"] == True) & (unet_myocardium_data["quality_controlled"] == True)
]
restrictiveCM_myocardium_data = unet_myocardium_data[
    (unet_myocardium_data["restrictiveCM_status"] == True) & (unet_myocardium_data["quality_controlled"] == True)
]
nonischemic_myocardium_data = unet_myocardium_data[
    (unet_myocardium_data["ischemic_disease"] == True) & (unet_myocardium_data["quality_controlled"] == True)
]
ischemic_myocardium_data = unet_myocardium_data[
    (unet_myocardium_data["nonischemic_disease"] == True) & (unet_myocardium_data["quality_controlled"] == True)
]
normal_myocardium_data = unet_myocardium_data[
    (unet_myocardium_data["nonischemic_disease"] == False)
    & (unet_myocardium_data["ischemic_disease"] == False)
    & (unet_myocardium_data["quality_controlled"] == True)
]

VAE_myocardium_data = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/latent_df_contrasted.txt"), sep=" "
)
covariates = pd.read_csv(
    os.path.join(BASE_DIR, "ukbb_code/anna_code/preprocessing/covariates.txt"), delimiter="\t"
)


def prepare_covarites(phenotypes, covariates, save_name):
    phenotypes_no_duplicates = phenotypes.drop_duplicates(subset=["IID"], keep="first")
    phenotypes_no_duplicates["IID"] = phenotypes_no_duplicates["IID"].astype(int)

    merged_df = pd.merge(phenotypes_no_duplicates, covariates, on="IID")
    merged_df.replace(-1000, np.nan, inplace=True)
    merged_df = merged_df.dropna()

    phenotypes_trimmed = merged_df[["FID", "IID", "0", "1", "2", "3", "4", "5"]]
    covariates_trimmed = merged_df[list(covariates.columns)]

    phenotypes_trimmed.to_csv(
        os.path.join(BASE_DIR, f"shriya/SHMOLLI-VAE-output/{save_name}_phenotypes_trimmed.txt"),
        sep="\t",
        index=False,
    )
    covariates_trimmed.to_csv(
        os.path.join(BASE_DIR, f"shriya/SHMOLLI-VAE-output/{save_name}_covariates_trimmed.txt"),
        sep="\t",
        index=False,
    )

    return phenotypes_trimmed, covariates_trimmed


phenotypes_trimmed, covariates_trimmed = prepare_covarites(VAE_myocardium_data, covariates, "VAE_dimensions")

# Sanity check: flag phenotype/covariate pairs with a nominal (p<0.1) correlation.
for phenotype in phenotypes_trimmed.columns:
    for covariate in covariates_trimmed.columns:
        corr, p_value = pearsonr(phenotypes_trimmed[phenotype], covariates_trimmed[covariate])
        if p_value < 0.1:
            print(phenotype, covariate)

prepare_covarites(HCM_myocardium_data, covariates, "HCM")
prepare_covarites(DCM_myocardium_data, covariates, "DCM")
prepare_covarites(valvular_myocardium_data, covariates, "valvular")
prepare_covarites(amyloidosis_myocardium_data, covariates, "amyloidosis")
prepare_covarites(restrictiveCM_myocardium_data, covariates, "restrictiveCM")
prepare_covarites(nonischemic_myocardium_data, covariates, "nonischemic")
prepare_covarites(ischemic_myocardium_data, covariates, "ischemic")
prepare_covarites(normal_myocardium_data, covariates, "normal")

# ---------------------------------------------------------------------------
# Remap the VAE-dimensions / non-ischemic / normal residual-phenotype files
# to application-24983 IDs (needs 02_ancestry_and_id_mapping.py's
# patient_mapping table to already be available).
# ---------------------------------------------------------------------------

patient_mapping = pd.read_table(os.path.join(BASE_DIR, "shriya/ukb22282_24983_mapping.tsv"), header=None)


def reverse_mapped_ID(id_to_find, mapping_df):
    if id_to_find in mapping_df[0].values:
        row_index = mapping_df[mapping_df[0] == id_to_find].index[0]
        return int(mapping_df.loc[row_index, 1])
    return None


def transform_residuals_IDs(save_name):
    """Remap a *_phenotypes.no_outliers.residuals.qnorm.txt file's IDs to application 24983."""
    phenotypes_path = os.path.join(
        BASE_DIR, f"shriya/SHMOLLI-VAE-output/{save_name}_phenotypes.no_outliers.residuals.qnorm.txt"
    )
    imputed_path = os.path.join(
        BASE_DIR,
        f"shriya/SHMOLLI-VAE-output/{save_name}_phenotypes_imputed.no_outliers.residuals.qnorm.txt",
    )

    imputed_residuals = pd.read_csv(phenotypes_path, sep="\t")

    for index, row in imputed_residuals.iterrows():
        mapped_IID = reverse_mapped_ID(int(row["IID"]), patient_mapping)
        imputed_residuals.at[index, "IID"] = mapped_IID
        imputed_residuals.at[index, "FID"] = mapped_IID

    imputed_residuals = imputed_residuals.dropna()
    imputed_residuals.to_csv(imputed_path, sep="\t", index=False)
    print(f"Saved: {imputed_path}")


transform_residuals_IDs("VAE_dimensions")
transform_residuals_IDs("nonischemic")
transform_residuals_IDs("normal")
