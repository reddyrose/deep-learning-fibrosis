"""
Quality-controls the U-Net myocardium/septum T1 percentile outputs (donut-shape
contour check on every subject's mask), then regresses hematocrit (and
hematocrit+hypertension) out of the T1 distribution metrics.

Split out of the original 03_phenotypes/01_SMHOLLI_tranformer_phenotype_associations.ipynb
during repository cleanup -- see docs/REVIEW_REQUIRED.md.
"""

import os

import cv2
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.linear_model import LinearRegression
from tqdm import tqdm

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR = "."

# ---------------------------------------------------------------------------
# Load percentile outputs from 01_imaging/deploy_unet_segmentation.py and the
# UK Biobank clinical/disease dataset.
# ---------------------------------------------------------------------------

unet_myocardium_data = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/percentiles_T1.csv")
)
unet_septum_data = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-septum/mean_T1.csv")
)
unet_septum_data = unet_septum_data.drop(columns=["Unnamed: 0"])

unet_myocardium_data["Patient_ID"] = unet_myocardium_data["Patient_ID"].str[:7]
unet_myocardium_data = unet_myocardium_data.rename(columns={"Patient_ID": "id"})
unet_myocardium_data = unet_myocardium_data.sort_values(by="id")
unet_myocardium_data.reset_index(drop=True, inplace=True)

# Remove patients that the model was not able to segment
unet_myocardium_data = unet_myocardium_data[unet_myocardium_data["Mean_T1"] != 0]

data_1 = pd.read_csv(
    os.path.join(BASE_DIR, "bruna/lvedv/ukbb_all_no_exclusion_all_2_and_3_with_CMR_and_MR"),
    delimiter="\t",
)

# ---------------------------------------------------------------------------
# Mask quality control: confirm each segmentation forms the expected donut
# shape (endocardial + epicardial ring), matching the production QC rule
# used elsewhere in the pipeline (see 01_imaging/unet_quality_control.py).
# ---------------------------------------------------------------------------

images_path = os.path.join(BASE_DIR, "shriya/UKBB_SHMOLLI-pngimages")
masks_path = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/SAM_masks")
mask_files = [os.path.join(masks_path, filename) for filename in sorted(os.listdir(masks_path))]


def check_completeness(contour):
    """Check if myocardial ring has large angular gaps."""
    if len(contour) < 10:
        return 0.0

    M = cv2.moments(contour)
    if M["m00"] == 0:
        return 0.0

    center = np.array([M["m10"] / M["m00"], M["m01"] / M["m00"]])
    points = contour[:, 0, :]

    angles = [np.arctan2(p[1] - center[1], p[0] - center[0]) for p in points]
    angles = sorted([(a + 2 * np.pi) % (2 * np.pi) for a in angles])

    gaps = [angles[i + 1] - angles[i] for i in range(len(angles) - 1)]
    gaps.append((2 * np.pi - angles[-1]) + angles[0])  # wrap-around gap
    max_gap = max(gaps)

    # Complete rings shouldn't have gaps > 60 degrees
    return max(0, 1 - max(max_gap - np.pi / 3, 0) / np.pi)


def check_quality(image_path):
    image = np.array(Image.open(image_path))
    image = image[..., np.newaxis]
    binary_image = (image > 0).astype(np.uint8)
    contours, _ = cv2.findContours(binary_image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    circle_count = sum(1 for c in contours if cv2.arcLength(c, True) > 0)
    quality = circle_count == 2

    if not quality and contours:
        main_contour = max(contours, key=cv2.contourArea)
        completeness_score = check_completeness(main_contour)
        quality = completeness_score > 0.98

    return quality


def find_mask_file_with_id(mask_files, id_value):
    """Find the mask file in mask_files whose filename contains the given id."""
    return [file for file in mask_files if str(id_value) in file][0]


unet_myocardium_data["quality_controlled"] = False
for index, row in tqdm(
    unet_myocardium_data.iterrows(), total=len(unet_myocardium_data), desc="Processing patients"
):
    patient_id = row["id"]
    mask_file = find_mask_file_with_id(mask_files, patient_id)
    unet_myocardium_data.loc[index, "quality_controlled"] = check_quality(mask_file)

clean_myocardium_data = unet_myocardium_data[unet_myocardium_data["quality_controlled"] == True]
clean_myocardium_data = clean_myocardium_data.drop("quality_controlled", axis=1)
clean_myocardium_data["id"] = clean_myocardium_data["id"].astype(str)

myocardium_csv_path = os.path.join(
    BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/cleaned_T1_percentiles.csv"
)
clean_myocardium_data.to_csv(myocardium_csv_path)

# ---------------------------------------------------------------------------
# Regress hematocrit (and hematocrit + hypertension) out of the T1
# distribution metrics.
# ---------------------------------------------------------------------------

clean_myocardium_data = pd.read_csv(myocardium_csv_path)

hypertension_patients = list(
    data_1[data_1["icd10"].astype(str).str.contains("I10", na=False)]["id"]
)
clean_myocardium_data["hypertension_status"] = clean_myocardium_data["id"].isin(
    hypertension_patients
)

hematocrit_data = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/hemocrit_only_trimmed.txt"),
    sep="\t",
)

clean_myocardium_data["id"] = clean_myocardium_data["id"].astype("str")
hematocrit_data["IID"] = hematocrit_data["IID"].astype("str")

merged_data = pd.merge(
    clean_myocardium_data, hematocrit_data, left_on="id", right_on="IID", how="inner"
)
merged_data = merged_data.drop(columns=["Unnamed: 0", "FID", "IID"])

t1_columns = [
    "Mean_T1",
    "T1_Standard_Deviation",
    "T1_0.25th_Percentile",
    "T1_1th_Percentile",
    "T1_25th_Percentile",
    "T1_50th_Percentile",
    "T1_75th_Percentile",
    "T1_99th_Percentile",
    "T1_99.75th_Percentile",
]


def regress_out_covariates(df, outcome_cols, covariate_cols):
    """Regress out covariates from outcome variables and return residuals."""
    regressed_data = df.copy()

    for outcome_col in outcome_cols:
        X = df[covariate_cols].values
        y = df[outcome_col].values

        X_df = pd.DataFrame(X)
        y_series = pd.Series(y)
        mask = ~(X_df.isnull().any(axis=1) | y_series.isnull())
        X_clean = X[mask]
        y_clean = y[mask]

        new_col_name = f"{outcome_col}_regressed_{'_'.join(covariate_cols)}"
        if len(X_clean) > 0:
            reg = LinearRegression()
            reg.fit(X_clean, y_clean)
            y_pred = np.full(len(df), np.nan)
            y_pred[mask] = reg.predict(X_clean)
            regressed_data[new_col_name] = y - y_pred
        else:
            regressed_data[new_col_name] = np.nan

    return regressed_data


print("Regressing out hematocrit...")
merged_data = regress_out_covariates(merged_data, t1_columns, ["hematocrit"])
print("Regressing out hematocrit and hypertension...")
merged_data = regress_out_covariates(merged_data, t1_columns, ["hematocrit", "hypertension_status"])

regressed_csv_path = os.path.join(
    BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/cleaned_T1_percentiles_HHregressed.csv"
)
merged_data.to_csv(regressed_csv_path)
print(f"Saved: {regressed_csv_path}")
