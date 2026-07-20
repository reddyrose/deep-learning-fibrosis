# Validation checks

Last run 2026-07-20.

- **Python:** all 17 `.py` files parse successfully with `python3 -m py_compile`.
- **Shell:** all 23 `.sh` files present.
- **R:** all 14 `.R` files parse successfully (`Rscript -e "parse(...)"`, R 4.4).
- **Notebooks:** all 14 `.ipynb` files are valid JSON. Cell outputs, `execution_count`, and Colab-specific metadata (`colab`, `executionInfo`, `outputId`) are cleared from every notebook; source cells are otherwise unmodified.
- **Credential-pattern scan:** no matches for common password, token, API-key, or private-key patterns anywhere in the tracked tree.
- **Hardcoded-path scan:** no remaining `/oak/`, `/content/drive/`, `/Users/`, `/home/`, or `/scratch/` references outside explanatory comments across `.py`, `.sh`, `.R`, and `.ipynb` files.
- **Large/data files:** no `.csv`, `.bed`, `.bim`, `.fam`, `.h5`, or `.hdf5` files are tracked by git; the two CVAE `.weights.h5` files are kept locally for reference and excluded via `.gitignore`.
- **Provenance:** every tracked file is listed in `docs/MANIFEST.tsv` with size, SHA-256 checksum, and origin.
- **Cross-references:** every file path named in a `README.md` (as a markdown link or in backticks) resolves to a real file in the repository, or is documented as a runtime-generated output.

These checks establish parseability, path portability, and file hygiene. They do not execute the pipeline; running the numbered folders in order against real UK Biobank data has not been re-verified end to end from this checked-out state.
