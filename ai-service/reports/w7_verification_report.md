# W7 verification report

Ngày: 2026-10-25. Branch `feature/ai-dataset-inspection`, HEAD `25e1eaa529f02292d31c40914624aad1fec8c9ee`. Python 3.11.0; PyTorch `2.11.0+cu128`; CUDA available `True` trên máy này. Không chạy lại W5 official test hoặc huấn luyện.

| Kiểm tra | Before | After | Kết quả |
|---|---|---|---|
| `python -m pytest ai-service/tests -q` | 34 passed (10.80 s) | 34 passed (10.57 s) | PASS |
| Checkpoint SHA-256 | `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada` | cùng hash, gồm rc2 ZIP | MATCH |
| `/health` | 200 `alive` | 200 `alive`; rc2 ZIP cũng 200 | PASS |
| `/ready` | 200, CUDA, threshold 0.9 | giống before; rc2 ZIP cũng vậy | MATCH |
| `/v1/infer` validation | 37 predictions | 37 predictions; rc2 ZIP cũng 37 | MATCH |
| Spot IDs/order, `raw_label`, `label` | lưu `runs/w7/before.json` | `runs/w7/after.json` | MATCH tuyệt đối |
| `confidence`, `scores`, threshold | before response | after response | MATCH với `rel_tol=abs_tol=1e-6` |
| `model_version` | `mobilenetv3-small-w2-488ed38efe01` | cùng version local/rc2 | MATCH |
| Development UNKNOWN | `raw_label=empty`, `label=unknown` | cùng kết quả local/rc2; rc2 confidence `0.7355409860610962` | MATCH |
| Polygon/ảnh lỗi | HTTP 422 `INVALID_POLYGON`/`INVALID_IMAGE` | cùng mã local/rc2 | MATCH |
| Legacy CLI | Baseline suite có test `baseline_utils` | `check_w1_splits.py` PASS; help của train/evaluate/analyze/inspect/prepare chạy | PASS |
| W6 rc1 ZIP SHA-256 | `22a99aee8dac43f5f26a5af60da48df39246b882f7503b13ddc51a8f42c2a4e2` | cùng hash; verifier PASS 20 files | MATCH |
| W7 rc2 ZIP | Chưa có | SHA-256 `6073421790203b850f71e6b013ad49a2ae3b42417ec00ec08236483a1603b27a`; verifier PASS 21 files | PASS |

`scripts/w7_regression.py` gọi FastAPI TestClient với model thật/CUDA, so toàn bộ response nghiệp vụ trừ `processing_time_ms`, dùng ảnh và polygon validation; không đưa ground truth vào service. `scripts/demo_release.py --version v0.1.0-rc2` giải nén ZIP và gọi Uvicorn HTTP thật. Một lần smoke rc2 ghi `processing_time_ms=583.524`; đây **không phải benchmark latency**. Source `src/*.py` được đóng gói trong rc2 khớp byte-for-byte với tám file nguồn tương ứng tại thời điểm build; release manifest và checksums bảo vệ bản snapshot. Source commit trong manifest là HEAD nền, còn W1–W7 source hiện chưa commit. W3 threshold SHA-256 `cb4270f8adae58ec4dede8e2b9267896523f120b74da614f1328f9a68d84784a`; config inference SHA-256 `37390a022a2dc75d8737dca22a9e3cc62d709cef7af52b343fd0b9f6445160d8` được W5 frozen config xác nhận bởi release builder.

Kết quả W5 historical chỉ áp dụng vì checkpoint, config, preprocessing, threshold, class order và output regression không đổi; không có test tuning mới. Phạm vi verification là UFPR04 validation/development và machine hiện tại; camera khác, 100 polygon thật khác nhau, production readiness và FULL false-alarm rate vẫn chưa được đánh giá. `pip check` PASS. `git diff --check` không có whitespace error (Git chỉ cảnh báo line ending README). Không có file staged; các ZIP/weights vẫn Git ignored.
