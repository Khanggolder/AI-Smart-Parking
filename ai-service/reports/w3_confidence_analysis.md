# W3 — Validation confidence and UNKNOWN candidate

## Method

The frozen W2 MobileNetV3-Small checkpoint at `ai-service/runs/mobilenetv3_gpu/best.pt` was evaluated on all 720 UFPR04 validation crops. The class order is `empty = 0`, `occupied = 1`. The training and validation manifests match the checksums stored in the checkpoint. The held-out test images were not loaded for inference or threshold selection. No training, model architecture change, or source-crop rewrite was performed.

Inference uses 224 × 224 RGB images with ImageNet mean `[0.485, 0.456, 0.406]` and standard deviation `[0.229, 0.224, 0.225]`. W1 crops use polygon masking. UNKNOWN is emitted when the maximum of the two softmax outputs is **strictly less than** the configured threshold. Softmax scores are not calibrated probabilities of correctness.

Run on CUDA with PyTorch 2.11.0+cu128, threshold 0.90, batch size 16. Checkpoint SHA-256: `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`. The checkpoint selected epoch 2.

## Validation results

Raw classification was correct on 720/720 crops: 348 empty and 372 occupied, with zero observed errors. At the 0.90 candidate threshold, 714 predictions were accepted and 6 were UNKNOWN (coverage 99.17%). Of the six abstentions, two were truly empty and four were truly occupied. Accepted accuracy was 714/714 on this validation split.

Maximum softmax score: minimum 0.5434, median 1.0000, fifth percentile 0.9992. The minimum was 0.7351 for true empty crops and 0.5434 for true occupied crops. Most scores are clustered near 1.0; the descriptive 10-bin ECE is 0.00264. That number is not proof of calibration, especially with no validation errors.

| Threshold | Accepted | UNKNOWN | Coverage | UNKNOWN: empty / occupied | Accepted accuracy |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 720 | 0 | 100.00% | 0 / 0 | 100% |
| 0.70 | 719 | 1 | 99.86% | 0 / 1 | 100% |
| 0.80 | 717 | 3 | 99.58% | 1 / 2 | 100% |
| 0.90 | 714 | 6 | 99.17% | 2 / 4 | 100% |
| 0.95 | 712 | 8 | 98.89% | 3 / 5 | 100% |
| 0.98 | 704 | 16 | 97.78% | 7 / 9 | 100% |
| 0.99 | 702 | 18 | 97.50% | 9 / 9 | 100% |

The full 2 × 3 confusion matrix for every threshold, counts, distribution bins, low-score sample paths, and per-class quantiles are in `ai-service/runs/mobilenetv3_gpu/confidence/val_confidence_report.json`. `val_predictions.csv` contains all 720 rows with true label, raw class, both softmax scores, maximum score, correctness, and final UNKNOWN decision. The same directory contains `val_confidence_distribution.png`, `lowest_confidence_crops.jpg` (24 lowest-score crops), and `threshold_candidate.json`.

## Visual review of low-score crops

The lowest-score occupied crops show dark vehicles, and some vehicles are partly obscured by vegetation or fall near an edge of the narrow masked crop. Several low-score empty crops contain prominent foliage or very little visible parking surface. These are visible characteristics of this gallery, not a verified cause of the model's scores. No raw validation classification errors were available to inspect. The gallery does not establish performance for shadows, nighttime scenes, different cameras, or all occlusion patterns.

## Synthetic sensitivity check

The same 720 validation crop files were transformed **in memory** using brightness 0.6, contrast 0.5, and a centered gray rectangle covering about 35% of image width and height. The separate `synthetic_sensitivity_report.json` records:

| Synthetic change | Raw correct | UNKNOWN at 0.90 | Accepted correct / accepted |
|---|---:|---:|---:|
| Brightness 0.6 | 719/720 | 8 | 712/712 |
| Contrast 0.5 | 720/720 | 7 | 713/713 |
| Center occlusion 35% | 709/720 | 21 | 696/699 |

The occlusion perturbation left **three wrong predictions accepted**. This demonstrates a limitation of max-softmax abstention on a controlled perturbation. These altered copies are not independent real-world samples and cannot establish production accuracy or optimal threshold.

## Candidate configuration and W4 handoff

The local `threshold_candidate.json` records threshold `0.90`, class order, normalization, crop mode, checkpoint hash, selected epoch, and status `candidate_not_production_validated`. The value is a starting configuration for W4, **not an optimized or production-validated threshold**. Validation has no raw mistakes, so it cannot measure whether UNKNOWN rejects ordinary model errors. Evaluation on independent camera conditions and labeled hard cases is needed before choosing a production threshold. Keep ground truth in evaluation only; inference should use the image and model scores.

For W4, load the frozen checkpoint and candidate configuration, check their architecture/class order/hash, apply the same crop preprocessing, and expose the raw class, both scores, maximum score, and final label. Preserve UNKNOWN as a distinct outcome. Collect labeled low-light, occluded, shifted-camera, and empty-with-object examples for a separate error/coverage study before promoting the candidate threshold.

Verification: `python -m pytest ai-service/tests -q` passed **14 tests**. The train, validation, and test manifest SHA-256 values and checkpoint hash remained unchanged after analysis.
