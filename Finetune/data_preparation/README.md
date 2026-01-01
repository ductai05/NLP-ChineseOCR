# Data Preparation

This directory contains scripts to prepare the dataset for fine-tuning PaddleOCR.

# Usage
1.  Ensure the source datasets (CWKB and NomNaOCR) are available locally.
2.  Update the path constants in `data_prep.py` if necessary:
    - `FINAL_DATASET_DIR`: Path to CWKB dataset.
    - `NOMNAOCR_DIR`: Path to NomNaOCR dataset.
    - `OUTPUT_DIR`: Path where the processed dataset will be saved.
3.  Run the script:
    ```bash
    python data_prep.py
    ```
