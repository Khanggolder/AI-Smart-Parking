# W5 – Independent test evaluation

## Protocol and provenance

The W2 MobileNetV3-Small checkpoint, W3 threshold, split manifests and evaluation method were inspected and frozen in `runs/mobilenetv3_gpu/w5_evaluation/frozen_evaluation_config.json` **before** reading test images. Checkpoint SHA-256: `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`; test manifest SHA-256: `684b8a49e82b7e2c2a9b22f4d97d1ca85c663a26e4e2fbacc69ddabed2cb4e9b`. W2 checkpoint records the same train/val/test manifest hashes; no cross-split date, image or crop overlap was found. Class order is `empty`, `occupied`; threshold is exactly `0.90`. One official test inference pass was run over the 740 saved W1 JPEG crops using validation transforms (RGB, 224×224, ImageNet normalization), `eval()` and `torch.inference_mode()`. Ground-truth labels were sent only to metric calculations, never to `ModelLoader.predict`.

`test_predictions.csv`, `test_metrics.json`, `unknown_metrics.json`, `test_confusion_matrix.png`, `error_analysis.json` and `error_gallery.jpg` are in the ignored W5 run directory. The evaluation command refuses to overwrite official outputs or make a second pass.

## Raw classifier – independent test

| Metric | Value |
|---|---:|
| Samples | 740 |
| Accuracy | 97.973% (725/740) |
| Macro precision | 97.800% |
| Macro recall | 97.870% |
| Macro F1 | 97.835% |
| Empty precision / recall / F1 | 98.488% / 98.276% / 98.382% |
| Occupied precision / recall / F1 | 97.112% / 97.464% / **97.288%** |

Confusion matrix, ground truth rows × prediction columns (`empty`, `occupied`):

| True | Pred empty | Pred occupied |
|---|---:|---:|
| Empty | 456 | 8 |
| Occupied | 7 | 269 |

There are 7 false empty and 8 false occupied predictions. **NFR-01 / occupied-F1 ≥ 0.90: achieved on this independent day-split test**, with observed F1 `0.972875`. This result represents this UFPR04 test sample, not other cameras or weather conditions.

By day: 2012-12-21 has 370 crops (94 empty, 276 occupied), accuracy 97.568%, macro-F1 96.846%. 2012-12-24 has 370 crops, all **empty**, accuracy 98.378% with 6 false occupied. The metrics helper assigns occupied F1 of 0 when no occupied ground truth exists; its day-level macro-F1 of 49.591% must not be interpreted as observed occupied performance for that day. Both days are Sunny.

## Selective classifier at the frozen 0.90 threshold

| Metric | Value |
|---|---:|
| Accepted | 712 |
| UNKNOWN | 28 (21 true empty, 7 true occupied) |
| Coverage / UNKNOWN rate | 96.216% / 3.784% |
| Accepted accuracy | 99.719% (710/712) |
| Accepted errors | 2 (0.281% of accepted; 0.270% of all samples) |
| Empty recall, UNKNOWN counted as miss | 95.474% |
| Occupied recall, UNKNOWN counted as miss | 96.739% |

Selective confusion matrix, ground truth rows × output columns (`empty`, `occupied`, `unknown`):

| True | Empty | Occupied | UNKNOWN |
|---|---:|---:|---:|
| Empty | 443 | 0 | 21 |
| Occupied | 2 | 267 | 7 |

The raw classifier made 15 errors; UNKNOWN rejected 13 of them, while **2 false empty predictions were accepted**. Thus 2/15, or **13.333% of raw errors**, passed the threshold. Their scores were 0.925317 and 0.949709. Scores are maximum softmax outputs and are **not calibrated probabilities of correctness**. Reporting accepted accuracy alone would hide the 28 abstentions and the reduced recall above.

## Error analysis

`error_analysis.json` lists all 15 raw errors with crop path, date, camera, true/predicted labels, confidence and UNKNOWN status. `error_gallery.jpg` shows false empty, false occupied, all UNKNOWN, lowest-confidence and accepted-error groups. Visual review shows many difficult crops dominated by vegetation, shadows or dark imagery; some occupied vehicles are difficult to see within the polygon. These are visual observations, not verified root-cause labels. The two accepted false empty crops are both from 2012-12-21, confidence 0.9253 and 0.9497.

## Validation-only hard cases

Deterministic transforms were applied **in memory** to the 720 validation JPEG crops. Original dataset files, checkpoint and threshold were unchanged. These experiments measure sensitivity, not deployed-camera accuracy.

| Scenario | Raw accuracy | UNKNOWN rate | Accepted errors |
|---|---:|---:|---:|
| Original validation JPEG | 100.000% | 0.833% | 0 |
| Synthetic low light ×0.5 | 99.306% | 1.389% | 1 |
| Synthetic contrast ×0.5 | 100.000% | 0.972% | 0 |
| Synthetic shadow over left side | 96.667% | 7.639% | 3 |
| Synthetic centered occlusion 35% | 98.472% | 3.056% | 3 |

The raw data are in `hard_cases_synthetic_val.json`. Quantified real labeled sets for off-center parking, objects in empty spots, other camera angles and specific foliage/shadow tags were unavailable. No per-scenario accuracy is claimed for those conditions. Error-gallery examples provide qualitative evidence only.

## W1 JPEG versus W4 in-memory crop

The comparison uses 100 equally spaced **validation** rows, the same annotation polygon IDs and exact normalized-to-pixel round trip. All 100 polygon coordinate arrays matched. Saved W1 JPEG versus direct W4 pixel mean absolute difference was 0.399 intensity units, maximum individual channel difference 39. Mean confidence difference was 0.00238, maximum 0.23094. **One raw label changed; no final label changed** because both paths returned UNKNOWN for that case. The changed crop was `2012-12-18/7546449674bc21.jpg`: W1 raw `empty` at 0.7384, W4 raw `occupied` at 0.5074. This demonstrates that low mean pixel difference can matter near a decision boundary. Detailed rows are in `preprocessing_consistency_val.json`; no preprocessing was changed based on test results.

## FULL alert

**FULL false-alarm rate: NOT EVALUATED — insufficient complete snapshot ground truth**

The test manifest has 20 images with 37 selected crops each, but its annotation IDs are image-specific and it does not establish stable production spot IDs or a certified complete lot inventory. Counting these crops as a whole configured lot would manufacture a FULL result. FULL remains backend logic: only all known valid spots occupied may imply FULL; any empty or UNKNOWN prevents a certain FULL alert.

## Remaining handoff conditions

The threshold remains `candidate_not_production_validated`. Capture labeled hard cases from the target camera, complete snapshots with stable spot IDs, and other camera/weather conditions before production claims. If W6 changes model, preprocessing or threshold, select changes on new development data and reserve a **new** independent test set; this W5 test is now exposed. Preserve the W5 JSON/CSV/gallery artifacts and model hash when handing the frozen version to Nam.
