# NASA C-MAPSS Dataset (FD001 + FD003)

Committed sub-set of the NASA Prognostics CoE Turbofan Engine Degradation Simulation Data Set,
used to train `models/ridge-fd001-fd003-v1.0.joblib`. Plan 07-03 / MNT-01.

## Source

- **Authority:** NASA Prognostics Center of Excellence (PCoE)
- **Citation:** Saxena, A., Goebel, K., Simon, D., Eklund, N. (2008).
  *Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation.*
  International Conference on Prognostics and Health Management (PHM 2008).
- **Official URL:** https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
- **License:** US Government work — public domain.
- **Reproducible mirror used for this commit:**
  https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip

## Sub-datasets included

| Sub-dataset | Files                                        | Description                                           |
| ----------- | -------------------------------------------- | ----------------------------------------------------- |
| FD001       | `train_FD001.txt`, `test_FD001.txt`, `RUL_FD001.txt` | 100 train + 100 test units, single fault mode, single op condition |
| FD003       | `train_FD003.txt`, `test_FD003.txt`, `RUL_FD003.txt` | 100 train + 100 test units, 2 fault modes (HPC + Fan), single op condition |

Sub-datasets FD002 / FD004 are **intentionally excluded** (D-PM-02 — covers 2 textile fault
families is sufficient for PoC; FD002/FD004 add multi-op-condition complexity not needed).

## Schema

Space-separated text, no header. 26 columns per row, all numeric:

```
unit_number  time_cycles  op_setting_1  op_setting_2  op_setting_3  s1 s2 ... s21
```

See `cmapss/training.py::CMAPSS_COLUMNS` for the canonical Python list.

Canonical schema reference: https://github.com/makinarocks/awesome-industrial-machine-datasets/blob/master/data-explanation/C-MAPSS/README.md

## SHA256 Checksums

Verify integrity before any retrain:

```bash
sha256sum -c <(cat <<'EOF'
a19c8ec94931949d0485bdc35118206e9c81c4547b422efb9cf86f4ceddbceca  c-mapss-fd001/RUL_FD001.txt
3cda7109ce17bafb5443f2ac926cfcf88154b941b8c4cf95eb55d1ddd6f52851  c-mapss-fd001/test_FD001.txt
963b5e22825b34d8b21c69e1aeb4af3e647050eb672ee8834ba4b5d91d2de0f8  c-mapss-fd001/train_FD001.txt
df1e0566306b174a2de41c67a3e7a51877889598b78643fc3e5685259091b7cb  c-mapss-fd003/RUL_FD003.txt
299babd63c8d987cef079c4a425429f33b3a34797d803bbe2ad48c29dbd0d790  c-mapss-fd003/test_FD003.txt
2abbe9968cc5e8eb091980f51b20f62bb4127336d3482cb52071d53bf23329e2  c-mapss-fd003/train_FD003.txt
EOF
)
```

## File sizes (~13 MB total)

| File                  | Size  | Rows   |
| --------------------- | ----- | ------ |
| `train_FD001.txt`     | 3.4 M | 20 631 |
| `test_FD001.txt`      | 2.2 M | 13 096 |
| `RUL_FD001.txt`       | 429 B | 100    |
| `train_FD003.txt`     | 4.1 M | 24 720 |
| `test_FD003.txt`      | 2.7 M | 16 596 |
| `RUL_FD003.txt`       | 428 B | 100    |

## Refreshing the dataset

To replace the committed files with a fresh download from NASA:

1. Download the zip from the official URL or the S3 mirror above.
2. Extract `train_FD001.txt`, `test_FD001.txt`, `RUL_FD001.txt`, `train_FD003.txt`,
   `test_FD003.txt`, `RUL_FD003.txt`.
3. Replace the files under `c-mapss-fd001/` and `c-mapss-fd003/`.
4. **Recompute and update** the SHA256 table in this README — `sha256sum c-mapss-fd001/*.txt c-mapss-fd003/*.txt`.
5. Re-run training: `cd packages/sft-ml && uv run --project ../.. python -m sft_ml.cmapss.training`.
6. Re-run smoke tests: `cd packages/sft-ml && uv run --project ../.. pytest tests/ -v`.
7. Commit dataset + model + this README in the same PR.
