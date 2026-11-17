# Backend ↔ AI: cách tích hợp hiện tại

Backend nhận snapshot có JWT, lưu ảnh, phiên bản camera và danh sách ô đang hoạt động. [`ai_client.py`](../../backend/app/services/ai_client.py) gửi ảnh tới AI `POST /v1/infer` qua multipart `image`, `camera_id`, `spots_json`. Mỗi polygon lưu trong Backend dưới dạng `{x,y}` được chuyển thành cặp `[x,y]`; `spot_id` là UUID ổn định và giữ nguyên thứ tự. Bản thiết kế W1 từng dùng `/predict`; endpoint đang chạy là `/v1/infer`.

AI trả `raw_label`, nhãn cuối `label`, `confidence`, `scores`, `model_version`, `threshold` và `processing_time_ms`. Backend kiểm camera ID, số lượng/thứ tự spot ID, nhãn, scores và confidence trước khi ghi. [`snapshot_jobs.py`](../../backend/app/services/snapshot_jobs.py) lưu mọi prediction và `completed` trong một giao dịch; lỗi AI/timeout/response sai ghi job `failed`, không tạo `unknown` giả. `unknown` chỉ có khi max-softmax thấp hơn ngưỡng `0,90` của model rc2. Review của người dùng không ghi đè dự đoán AI gốc.

Backend tính summary từ nhãn hiệu lực, chỉ báo `FULL` khi mọi ô có xe và tách `STALE` theo thời điểm snapshot. Ảnh snapshot phải cùng kích thước với ảnh tham chiếu; cấu hình polygon được chụp lại khi tạo job. AI không có xác thực riêng, nên chỉ dùng trên loopback hoặc mạng Compose nội bộ.

Job hiện dùng `BackgroundTasks` trong tiến trình Backend: chưa có cơ chế tự khôi phục `queued`/`processing` sau restart, hoặc retry bền vững. [Báo cáo W6](../../backend/reports/w6_7_3_2_e2e_integration.md) ghi một lần chạy với AI thật và PostgreSQL trên **một ô**. Cần kiểm tra nhiều ô, tình huống `unknown`, lỗi AI và toàn bộ giao diện trên máy demo.

Gói rc2 không nằm trong Git. Trước khi chạy, kiểm ZIP SHA-256 `6073421790203b850f71e6b013ad49a2ae3b42417ec00ec08236483a1603b27a`, giải nén, chạy `verify_release.py` và kiểm `/ready`. Xem [hướng dẫn release](RELEASE_README.md), [API AI](AI_API_CONTRACT.md) và [backend README](../../backend/README.md).
