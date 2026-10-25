# Bàn giao AI API cho Nam

## Khởi chạy và kết nối

Release ZIP bị Git ignore, nên chỉ clone repo sẽ không có checkpoint. Khang cần chuyển `ai-smart-parking-model-v0.1.0-rc2.zip` qua kênh nội bộ được nhóm thống nhất; Nam kiểm SHA-256 ZIP `6073421790203b850f71e6b013ad49a2ae3b42417ec00ec08236483a1603b27a`, sau đó giải nén, chạy `verify_release.py` để kiểm `checksums.sha256`, cài Python 3.11 và dependency theo `README.md` trong gói, chạy Uvicorn `src.service:app`. Checkpoint là `model/best.pt`; threshold là `threshold_candidate.json`; config là `configs/inference.yaml`. Không hard-code đường dẫn Windows trong backend. Cấu hình URL backend tới service bằng biến môi trường, ví dụ `AI_SERVICE_URL=http://127.0.0.1:8001`; timeout trong [kế hoạch tích hợp](BACKEND_AI_INTEGRATION_PLAN.md) chỉ là giá trị ban đầu cho demo và phải đo lại trên máy đích. `AI_DEVICE=auto|cuda|cpu` thuộc service; không gắn trực tiếp GPU với backend.

Trình tự: backend nhận snapshot và camera ID → lấy polygon **đã lưu, đúng phiên bản camera** → gửi multipart theo [AI_API_CONTRACT.md](AI_API_CONTRACT.md) → xác minh HTTP 200, camera ID, số lượng/thứ tự và tập spot ID → lưu `raw_label`, `label`, `confidence`, `scores`, `model_version`, threshold và timestamp của snapshot → trả dữ liệu cho frontend. Không gửi nhãn thật trong request. Client mẫu trong repo `scripts/ai_http_client.py` và trong ZIP `client_example.py` đọc ảnh và polygon từ file JSON hoặc nguồn thật, không điền dự đoán.

`unknown` là trạng thái riêng, không mặc định thành `empty`; `raw_label` chỉ giúp audit. FULL và STALE là logic của backend. Chỉ kết luận FULL khi có snapshot hoàn chỉnh của danh sách ô cấu hình ổn định và chính sách UNKNOWN đã thống nhất; W5 chưa đo full false-alarm. Backend giữ kết quả snapshot cũ khi request mới thất bại và đánh dấu thời gian/stale theo chính sách của Nam.

Timeout/offline: không ghi prediction mới. HTTP 422: kiểm input ảnh, polygon, ID; không retry nguyên request không hợp lệ. HTTP 503 hoặc `/ready` không sẵn sàng: báo AI unavailable, retry có giới hạn sau backoff. HTTP 500/transport timeout: log request ID/camera ID và trạng thái nhưng không gán `unknown` giả. Không retry mù quáng tạo lịch sử duplicate; idempotency thuộc backend.

Service hiện chưa có auth; chỉ expose trong mạng nội bộ phù hợp, bind loopback khi chạy chung máy. Nếu Docker, để backend và AI cùng private network, không publish trực tiếp cổng AI ra Internet. Không đưa dữ liệu ảnh/đường dẫn nhạy cảm vào log công khai. Camera ID service chỉ echo, nên backend phải xác thực nguồn và kiểm cấu hình polygon của mình.

API `model_version` cố định theo SHA checkpoint: `mobilenetv3-small-w2-488ed38efe01`; release `v0.1.0-rc2` được ghi riêng trong manifest. Nam cần xác nhận mapping spot ID ổn định và lưu phiên bản polygon/camera; annotation ID UFPR04 không đáp ứng việc đó. Hai false empty được W5 chấp nhận ở threshold 0,90, vì vậy dashboard/logic nghiệp vụ không nên coi output là sự thật tuyệt đối.
