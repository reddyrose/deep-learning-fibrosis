# Validation checks

Last run 2026-07-30.

- **Python:** all 18 `.py` files parse successfully with `python3 -m py_compile`.
- **Shell:** all 23 `.sh` files present.
- **R:** all 14 `.R` files parse successfully (`Rscript -e "parse(...)"`, R 4.4).
- **Notebooks:** all 14 `.ipynb` files are valid JSON. Cell outputs, `execution_count`, and Colab-specific metadata (`colab`, `executionInfo`, `outputId`) are cleared from every original research notebook; source cells are otherwise unmodified. `demo/demo_walkthrough.ipynb` is a deliberate exception -- its outputs (plots, tables, printed statistics) are committed inline so the demo reads on GitHub without execution; see below.
- **Demo notebook execution:** `demo/demo_walkthrough.ipynb` re-executes end to end with 0 errors against the committed `demo/example_data/` (`jupyter nbconvert --to notebook --execute`), ~171s on a standard laptop CPU.
- **Credential-pattern scan:** no matches for common password, token, API-key, or private-key patterns anywhere in the tracked tree.
- **Hardcoded-path scan:** no remaining `/oak/`, `/content/drive/`, `/Users/`, `/home/`, or `/scratch/` references outside explanatory comments across `.py`, `.sh`, `.R`, and `.ipynb` files.
- **Large/data files:** no `.csv`, `.bed`, `.bim`, or `.fam` files are tracked by git. Two trained-model checkpoints are tracked as deliberate exceptions to the general `.h5`/`.weights.h5` exclusion (`01_imaging/myocardium-unet-256.h5`, `02_vae/cvae_16d_best.weights.h5`, both under 25MB); the alternate CVAE checkpoint (`cvae_16d_optimized.weights.h5`) remains git-ignored.
- **Provenance:** every tracked file is listed in `docs/MANIFEST.tsv` with size, SHA-256 checksum, and origin.
- **Cross-references:** every file path named in a `README.md` (as a markdown link or in backticks) resolves to a real file in the repository, or is documented as a runtime-generated output.

These checks establish parseability, path portability, and file hygiene. They do not execute the pipeline; running the numbered folders in order against real UK Biobank data has not been re-verified end to end from this checked-out state.
