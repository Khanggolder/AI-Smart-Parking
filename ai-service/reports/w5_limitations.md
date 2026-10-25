# W5 limits and W6 handoff

- The frozen test has 740 UFPR04 crops from **two Sunny days**. One day has no occupied samples. Results cannot establish cross-camera, rainy, night, seasonal or production accuracy.
- Two occupied spots were accepted as `empty` at confidence 0.9253 and 0.9497. The 0.90 UNKNOWN threshold remains a candidate, not production validated.
- Synthetic validation transforms reveal sensitivity to shadow and occlusion. They do not replace labeled real hard-case data. No defensible per-scenario metric exists yet for off-center parking, foreign objects in an empty spot or camera angle changes.
- W1 stored JPEG and W4 direct crop differ at the pixel level. In a 100-row validation comparison, one raw label changed, though final UNKNOWN status did not. W6 should retain versioned preprocessing and monitor this difference on target-camera examples.
- `FULL false-alarm rate: NOT EVALUATED — insufficient complete snapshot ground truth`. Current annotation IDs are not stable backend spot IDs. Collect whole-lot snapshots with stable spot configuration and reliable occupancy labels.
- The 1280×720 benchmark has 37 distinct polygons. The 50/100 spot load cases repeat polygons and are marked `synthetic workload`; no claim is made for 100 distinct real parking spaces.
- The W5 test has been used for final evaluation. Any future model, threshold or preprocessing change requires a new independent test set after selection on development data.
- The W5 run directory, checkpoint and W3 threshold JSON are Git ignored and must be transferred separately with SHA-256 values to Nam. AI API contract fields were not changed in W5.

W6 should gather labeled target-camera hard cases, complete snapshots and a fresh sealed holdout; verify polygon/camera versions; review accepted false-empty risk with Nam; and validate deployment latency with genuine 100-spot geometry if that scale is required.
