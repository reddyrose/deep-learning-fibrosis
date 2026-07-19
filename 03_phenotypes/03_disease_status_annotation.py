"""
Builds ICD-10-derived disease patient-ID lists (HCM, DCM, valvular disease,
amyloidosis, restrictive cardiomyopathy, ischemic/non-ischemic heart disease),
annotates the myocardium/septum T1 data with per-disease status columns, and
writes disease_patient_IDs.txt -- the file 04_pwas/03_PheWAS_delta_rank_test_T1_descriptive_statistics.ipynb
and 08_clinical_associations/02_mortality_curves_chi_squared.ipynb read (as
cardiac_ids_dict) for the HCM, Valvular, Amyloidosis, Ischemic, and
Non-Ischemic disease groups.

Two bugs were fixed relative to the original notebook cell during this split:
- DCM_status was being set from HCM_patients_ids (a copy-paste error) instead
  of DCM_patients_ids.
- The myocardium/septum merge referenced the HCM_status column before it was
  created; the merge now runs after disease-status annotation instead of
  before it.

Split out of the original 03_phenotypes/01_SMHOLLI_tranformer_phenotype_associations.ipynb
during repository cleanup -- see docs/REVIEW_REQUIRED.md.
"""

import os

import pandas as pd

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR = "."

unet_myocardium_data = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/percentiles_T1.csv")
)
unet_myocardium_data["Patient_ID"] = unet_myocardium_data["Patient_ID"].str[:7]
unet_myocardium_data = unet_myocardium_data.rename(columns={"Patient_ID": "id"})
unet_myocardium_data = unet_myocardium_data.sort_values(by="id").reset_index(drop=True)
unet_myocardium_data = unet_myocardium_data[unet_myocardium_data["Mean_T1"] != 0]

# unet_septum_data's `quality_controlled` column is pre-computed by
# 01_imaging/unet_quality_control.py and reused here as the QC flag for the
# whole-myocardium data below (cell 32's cross-check in the original notebook).
unet_septum_data = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-septum/mean_T1.csv")
)
unet_septum_data = unet_septum_data.drop(columns=["Unnamed: 0"])

data_1 = pd.read_csv(
    os.path.join(BASE_DIR, "bruna/lvedv/ukbb_all_no_exclusion_all_2_and_3_with_CMR_and_MR"),
    delimiter="\t",
)

# ---------------------------------------------------------------------------
# ICD-10-derived disease patient-ID lists.
# ---------------------------------------------------------------------------

HCM_patients = data_1[data_1["icd10"].str.contains(r"I421|I422", na=False)]
DCM_patients = data_1[data_1["icd10"].str.contains(r"I420", na=False)]
valvular_patients = data_1[data_1["icd10"].str.contains(r"I509|I089|I359", na=False)]
amyloidosis_patients = data_1[data_1["icd10"].str.contains(r"E85", na=False)]
restrictiveCM_patients = data_1[data_1["icd10"].str.contains(r"I425", na=False)]
ischemic_patients = data_1[data_1["icd10"].str.contains(r"I20|I21|I22|I23|I24", na=False)]
nonischemic_patients = data_1[data_1["icd10"].str.contains(r"I42|I50|I31|I34|I35", na=False)]
quality_patients = unet_septum_data[unet_septum_data["quality_controlled"] == True]

HCM_patients_ids = HCM_patients["id"].astype(str).tolist()
DCM_patients_ids = DCM_patients["id"].astype(str).tolist()
valvular_patients_ids = valvular_patients["id"].astype(str).tolist()
amyloidosis_patients_ids = amyloidosis_patients["id"].astype(str).tolist()
restrictiveCM_patients_ids = restrictiveCM_patients["id"].astype(str).tolist()
ischemic_patients_ids = ischemic_patients["id"].astype(str).tolist()
nonischemic_patients_ids = nonischemic_patients["id"].astype(str).tolist()
quality_patients_ids = quality_patients["id"].astype(str).tolist()

# ---------------------------------------------------------------------------
# Annotate the myocardium/septum data with per-disease status columns.
# ---------------------------------------------------------------------------

for df in (unet_myocardium_data, unet_septum_data):
    df["HCM_status"] = df["id"].isin(HCM_patients_ids)
    df["DCM_status"] = df["id"].isin(DCM_patients_ids)
    df["valvular_status"] = df["id"].isin(valvular_patients_ids)
    df["amyloidosis_status"] = df["id"].isin(amyloidosis_patients_ids)
    df["restrictiveCM_status"] = df["id"].isin(restrictiveCM_patients_ids)
    df["ischemic_disease"] = df["id"].isin(ischemic_patients_ids)
    df["nonischemic_disease"] = df["id"].isin(nonischemic_patients_ids)
    df["quality_controlled"] = df["id"].isin(quality_patients_ids)

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

unet_myocardium_data.to_csv(os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/mean_T1.csv"))
unet_septum_data.to_csv(os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-septum/mean_T1.csv"))

# ---------------------------------------------------------------------------
# Write disease_patient_IDs.txt -- consumed downstream by
# 04_pwas/03_PheWAS_delta_rank_test_T1_descriptive_statistics.ipynb and
# 08_clinical_associations/02_mortality_curves_chi_squared.ipynb.
# ---------------------------------------------------------------------------

unet_septum_ids = [
    id_ for id_, qc in zip(unet_septum_data["id"], unet_septum_data["quality_controlled"]) if qc
]

quality_patients_set = set(quality_patients_ids)
HCM_set = set(HCM_patients_ids)
DCM_set = set(DCM_patients_ids)
valvular_set = set(valvular_patients_ids)
amyloidosis_set = set(amyloidosis_patients_ids)
restrictiveCM_set = set(restrictiveCM_patients_ids)
ischemic_set = set(ischemic_patients_ids)
nonischemic_set = set(nonischemic_patients_ids)


def find_overlaps(results, category_set, category_name):
    overlaps = category_set.intersection(quality_patients_set)
    results[category_name] = {"ids": list(overlaps), "count": len(overlaps)}


results = {}
find_overlaps(results, HCM_set, "HCM")
find_overlaps(results, DCM_set, "DCM")
find_overlaps(results, valvular_set, "Valvular")
find_overlaps(results, amyloidosis_set, "Amyloidosis")
find_overlaps(results, restrictiveCM_set, "Restrictive CM")
find_overlaps(results, ischemic_set, "Ischemic")
find_overlaps(results, nonischemic_set, "Non-Ischemic")

all_overlaps = HCM_set.union(
    DCM_set, valvular_set, amyloidosis_set, restrictiveCM_set, ischemic_set, nonischemic_set
)
normal_patients_set = set(unet_septum_ids) - all_overlaps
results["Normal Patients"] = {"ids": list(normal_patients_set), "count": len(normal_patients_set)}

disease_ids_path = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/disease_patient_IDs.txt")
with open(disease_ids_path, "w") as file:
    for category, data in results.items():
        file.write(f"{category} IDs: {', '.join(map(str, data['ids']))}\n")
        file.write(f"Number of IDs in {category}: {data['count']}\n\n")

for category, data in results.items():
    print(f"Number of IDs in {category}: {data['count']}")
print(f"Saved: {disease_ids_path}")

# ---------------------------------------------------------------------------
# Merge myocardium + septum data with the broader UK Biobank phenotype
# dataset. Runs after disease-status annotation because it drops the
# HCM_status column, which must already exist.
# ---------------------------------------------------------------------------

clean_myocardium_data = unet_myocardium_data[unet_myocardium_data["quality_controlled"] == True].copy()
clean_septum_data = unet_septum_data[unet_septum_data["quality_controlled"] == True].copy()

clean_myocardium_data = clean_myocardium_data.rename(
    columns={
        "Mean_T1": "Mean_T1_myocardium",
        "T1_50th_Percentile": "T1_50th_Percentile_myocardium",
        "T1_Standard_Deviation": "T1_Standard_Deviation_myocardium",
        "T1_99th_Percentile": "T1_99th_Percentile_myocardium",
        "T1_75th_Percentile": "T1_75th_Percentile_myocardium",
    }
)

clean_myocardium_data = clean_myocardium_data.drop("quality_controlled", axis=1)
clean_septum_data = clean_septum_data.drop("quality_controlled", axis=1)
clean_septum_data = clean_septum_data.drop("HCM_status", axis=1)

data_1["id"] = data_1["id"].astype(str)
clean_myocardium_data["id"] = clean_myocardium_data["id"].astype(str)
clean_septum_data["id"] = clean_septum_data["id"].astype(str)

merged_clean_myocardium_data = pd.merge(clean_myocardium_data, data_1, on="id")
merged_clean_all_data = pd.merge(clean_septum_data, merged_clean_myocardium_data, on="id")

myocardium_csv_path = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/cleaned_mean_T1_allpheno.csv")
septum_csv_path = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-septum/cleaned_mean_T1_allpheno.csv")
merged_clean_all_data.to_csv(myocardium_csv_path, index=False)
merged_clean_all_data.to_csv(septum_csv_path, index=False)
print(f"Saved: {myocardium_csv_path}")
print(f"Saved: {septum_csv_path}")
