# W1 – UFPR04 prepared dataset

- Crop mode: `mask` (polygon mask + bbox when `mask`); letterbox to 224 x 224.
- Seed: `42`; source images per selected day: at most `10`.
- Split unit: **calendar date** for UFPR04; no date or source panorama shared across splits.
- These are samples for the preparation pipeline, not the final model benchmark.
- `annotation_id` is an identifier in source annotation, not stable production spot_id.
- For a final training dataset, increase days/images and recheck split distribution.

| Split | Days | Panoramas | Empty | Occupied | Crops |
|---|---:|---:|---:|---:|---:|
| train | 8 | 80 | 1724 | 1176 | 2900 |
| val | 2 | 20 | 348 | 372 | 720 |
| test | 2 | 20 | 464 | 276 | 740 |

## Skipped items / anomalies

- `invalid_contour`: 0

## Dataset source

- MetaPKLot: https://github.com/DSBD-Research/MetaPKLot-Dataset
- PKLot images are CC BY 4.0; preserve attribution and review derivative distribution terms.
