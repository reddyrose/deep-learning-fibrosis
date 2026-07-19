"""
Validation check: compares whole-myocardium T1 metrics (this study's primary
approach) against septal-only T1 (the approach used by prior literature, e.g.
Nauffal et al. 2023) -- Bland-Altman agreement, correlation, and a t-test,
plus a broader Spearman/Pearson screen of septal T1 against every raw T1
percentile and VAE latent-dimension column.

Split out of the original 03_phenotypes/01_SMHOLLI_tranformer_phenotype_associations.ipynb
during repository cleanup -- see docs/REVIEW_REQUIRED.md.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import pearsonr, spearmanr, ttest_rel

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR = "."

phenotypes = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/cleaned_mean_T1_allpheno.csv"),
    low_memory=False,
)
latent_dimensions = pd.read_csv(
    os.path.join(
        BASE_DIR,
        "shriya/SHMOLLI-output-unet-myocardium-update2/cleaned_latent_dimentions_PHEWAS.no_outliers.residuals.qnorm.txt",
    ),
    sep="\t",
)
septal_T1 = pd.read_csv(os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-septum/mean_T1.csv"))

unfiltered_unet_t1_raw = pd.read_csv(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/percentiles_T1.csv")
)
unfiltered_unet_t1_raw["Patient_ID"] = [int(x[:7]) for x in unfiltered_unet_t1_raw["Patient_ID"]]

valid_images = np.load(
    os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/quality_ID_list.csv.npy")
).tolist()
valid_images = [int(x) for x in valid_images]


def bland_altman_plot(ground_truth, predicted):
    ground_truth = np.array(ground_truth)
    predicted = np.array(predicted)

    mean = np.mean([ground_truth, predicted], axis=0)
    diff = ground_truth - predicted
    mean_diff = np.mean(diff)
    std_diff = np.std(diff, axis=0)
    limits_of_agreement = 1.96 * std_diff
    t_statistic, p_value = ttest_rel(ground_truth, predicted)

    plt.figure(figsize=(8, 6))
    plt.scatter(mean, diff, color="blue", alpha=0.5)
    plt.axhline(mean_diff, color="gray", linestyle="--")
    plt.axhline(mean_diff + limits_of_agreement, color="red", linestyle="--")
    plt.axhline(mean_diff - limits_of_agreement, color="red", linestyle="--")
    plt.xlabel("Mean of Myocardium and Septum")
    plt.ylabel("Difference (Septum - Myocardium)")
    plt.title("Bland-Altman Plot")
    plt.grid(True)
    plt.show()

    return mean_diff, limits_of_agreement, std_diff, t_statistic, p_value


def get_stats(list1, list2):
    mean_diff, limits_of_agreement, std_diff, t_statistic, p_value = bland_altman_plot(list1, list2)
    print("Mean Difference:", mean_diff)
    print("Limits of Agreement:", limits_of_agreement)
    print("Standard Deviation of Differences:", std_diff)
    print("t-statistic:", t_statistic)
    print("p-value:", p_value)

    slope, intercept, r_value, p_value, std_err = stats.linregress(list1, list2)
    print(f"Slope: {slope}")
    print(f"Intercept: {intercept}")
    print(f"P-value: {p_value}")

    x = [i for i in range(700, 1200)]
    y = slope * np.array(x) + intercept
    plt.scatter(list1, list2, label="Data Points")
    plt.plot(x, y, color="blue", label="Best Fit Line")
    plt.xlabel("Septum")
    plt.ylabel("Myocardium")
    plt.title("Best Fit Line")
    plt.legend()

    t_stat, p_val = stats.ttest_ind(list1, list2, nan_policy="omit")
    print("T-Test results")
    print(f"t-statistic = {t_stat}, p-value = {p_val}")
    print(f"Mean of group 1 (Septum): {list1.mean()}")
    print(f"Mean of group 2 (Myocardium): {list2.mean()}")


get_stats(
    np.array(phenotypes["T1_Standard_Deviation_septum"]),
    np.array(phenotypes["T1_Standard_Deviation_myocardium"]),
)
get_stats(np.array(phenotypes["Mean_T1_septum"]), np.array(phenotypes["Mean_T1_myocardium"]))
get_stats(np.array(phenotypes["Mean_T1_septum"]), np.array(phenotypes["T1_75th_Percentile_myocardium"]))

# ---------------------------------------------------------------------------
# Broader screen: septal Mean_T1 vs. every raw T1 percentile / VAE latent
# dimension column (Spearman, then Pearson).
# ---------------------------------------------------------------------------

phenotypes_valid = septal_T1[septal_T1["id"].isin(valid_images)]
unfiltered_valid = unfiltered_unet_t1_raw[unfiltered_unet_t1_raw["Patient_ID"].isin(valid_images)]
latent_valid = latent_dimensions[latent_dimensions["IID"].isin(valid_images)]
target = phenotypes_valid[["id", "Mean_T1_septum"]].dropna().rename(columns={"id": "Patient_ID"})

for corr_name, corr_fn in [("spearman", spearmanr), ("pearson", pearsonr)]:
    results = []
    for df_name, df, id_col in [
        ("unfiltered_unet_t1_raw", unfiltered_valid, "Patient_ID"),
        ("latent_dimensions", latent_valid, "IID"),
    ]:
        df_renamed = df.rename(columns={id_col: "Patient_ID"})
        merged = target.merge(df_renamed, on="Patient_ID", how="inner")
        feature_cols = [c for c in df_renamed.columns if c != "Patient_ID"]

        for col in feature_cols:
            sub = merged[["Mean_T1_septum", col]].dropna()
            if len(sub) < 10:
                continue
            r, p = corr_fn(sub["Mean_T1_septum"], sub[col])
            results.append({"source": df_name, "feature": col, f"{corr_name}_r": r, "p_value": p})

    results_df = pd.DataFrame(results).sort_values("p_value")
    results_df["significant"] = results_df["p_value"] < 0.05

    print(f"\n=== {corr_name.title()} ===")
    print(f"Total comparisons: {len(results_df)}")
    print(f"Significant (p<0.05): {results_df['significant'].sum()}")
    print("Top 20 by |r|:")
    print(
        results_df.reindex(results_df[f"{corr_name}_r"].abs().sort_values(ascending=False).index)
        .head(20)
        .to_string(index=False)
    )
