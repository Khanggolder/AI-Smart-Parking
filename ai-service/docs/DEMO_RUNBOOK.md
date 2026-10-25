# Kịch bản demo AI v0.1.0-rc2

Điều kiện chung: giải nén release, kiểm hash, khởi động service, `/ready=200`; dùng ảnh UFPR04 validation 1280×720 và 37 polygon khác nhau từ `scripts/sample_snapshot.py` trong repo nguồn. Đây là input demo, không chuyển label annotation vào AI. Kiểm overlay ROI bằng mắt trên ảnh nguồn trước trình chiếu. Release ZIP không kèm dữ liệu ảnh. API `model_version` phải bằng manifest, threshold 0,90.

| Scenario | Input/thao tác | Kết quả mong đợi | Trạng thái |
|---|---|---|---|
| A Normal | Ảnh validation UFPR04, 37 polygon/ID `DEMO-001`…`DEMO-037`; `scripts/demo_release.py --version v0.1.0-rc2` | `/health`, `/ready`, `/v1/infer` 200; 37 prediction đúng thứ tự ID, schema đủ trường | Kiểm thực tế W7 |
| B UNKNOWN | Crop validation `2012-12-18/7546449674bc21.jpg`, polygon toàn ảnh; không ghép nhãn thật vào request | `raw_label=empty`, `label=unknown`, confidence khoảng 0,7355 | Đã chạy qua HTTP từ ZIP ở W6; đây là crop development, không phải snapshot toàn cảnh |
| C Polygon sai | Cùng ảnh, polygon tự giao `[[0,0],[1,1],[0,1],[1,0]]` | HTTP 422 `INVALID_POLYGON`, không có prediction | Kiểm thực tế W6 |
| D Service unavailable | Dừng AI service và gửi snapshot mới qua backend | Backend giữ kết quả cũ, ghi nhận lỗi và stale, không biến mất lịch sử | Chờ Nam tích hợp backend |
| E Reproducibility | `verify_release.py`, khởi động từ ZIP, `/ready` | Checkpoint hash đúng, `model_version` và threshold đúng manifest | Đã chạy qua HTTP từ ZIP ở W6 |

Không hard-code prediction để làm đẹp demo. Mọi kết quả AI hiển thị phải đến từ inference response. Kết quả trên ảnh validation không được trình bày là số đo test độc lập; W5 test đã được khóa.
