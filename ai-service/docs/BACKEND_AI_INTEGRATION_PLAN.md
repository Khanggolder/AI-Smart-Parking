# Kế hoạch nối backend với AI

Đây là đề xuất để Nam review, **chưa có adapter backend chạy**. Nguồn đối chiếu: [hợp đồng backend](../../docs/api/backend-api-contract-v1.md), [API AI](AI_API_CONTRACT.md) và `src/service.py`. Không tự đổi hợp đồng của Nam.

## Những chỗ cần chuyển đổi

| Nội dung | Thiết kế backend | AI service đang chạy | Việc backend cần làm |
|---|---|---|---|
| Upload công khai | `POST /api/v1/snapshots`, JWT, `camera_id`, `captured_at`, `image`; trả job `202` | Không có API snapshot hoặc database | Xác thực, lưu ảnh/thời gian và quản lý job |
| Gọi nội bộ | `POST /predict`, ảnh + JSON metadata | `POST /v1/infer`, multipart `image`, `camera_id`, `spots_json` | Gọi đúng endpoint/form field, cập nhật contract sau khi Nam duyệt |
| Polygon | Đỉnh dạng `{x,y}` normalized | Đỉnh dạng `[x,y]` normalized, 3–50 đỉnh/ô, 1–100 ô | Đổi từng đỉnh, giữ thứ tự và kiểm phiên bản cấu hình camera |
| ID ô/camera | UUID spot, mã hiển thị riêng; camera config version | `spot_id` là chuỗi 1–128 ký tự; chỉ echo `camera_id` | Gửi UUID ổn định, xác minh ID/thứ tự response; backend giữ config version |
| Dự đoán | Ví dụ `label`, `confidence`, `model_version`, `inference_ms` | `raw_label`, nhãn cuối `label`, `confidence`, `scores`; `model_version`, `threshold`, `processing_time_ms` ở mức response | Lưu cả nhãn cuối và raw; `processing_time_ms` không phải round-trip latency |
| Lỗi | Job async có thể `failed` | 413/415/422/503/500, lỗi handler có `error.code/message` | Không ghi dự đoán dở hoặc tạo `unknown` giả khi lỗi |

`empty=0`, `occupied=1`. AI trả `unknown` nếu max-softmax **nhỏ hơn** 0,90; `raw_label` và scores vẫn còn. UNKNOWN là nhãn cuối riêng, không phải lỗi truyền tải và không được đổi thành empty trong database/tổng hợp/UI. FULL và STALE do backend tính. Theo thiết kế hiện tại, có UNKNOWN thì không kết luận chắc chắn FULL.

## Trình tự tích hợp đề xuất

1. Backend nhận snapshot có xác thực; giữ `captured_at`, ảnh, camera ID, phiên bản cấu hình và danh sách UUID ô đang hoạt động cho job. Không gửi ground truth hay nhãn review sang AI.
2. Kiểm ảnh và polygon thuộc cùng cấu hình camera. Đổi `{x,y}` thành `[x,y]`, tạo `spots_json` gồm `spot_id` và polygon. AI chỉ nhận JPEG/PNG, tối đa 10 MiB, 20 triệu pixel, 1–100 ô và JSON tối đa 256 KiB.
3. Gửi multipart tới `/v1/infer`. Khi HTTP 200, xác minh `camera_id`, đúng số lượng và **đúng thứ tự** `spot_id`; confidence/scores hữu hạn trong `[0,1]`, nhãn hợp lệ, `model_version` không rỗng và threshold 0,90 cho bản này. Nếu response thiếu hoặc sai, hủy ghi toàn bộ job.
4. Lưu snapshot ID, thời gian chụp, phiên bản camera/polygon, UUID ô, `raw_label`, nhãn cuối, confidence, scores, model version và threshold. Nhãn nhân viên review ghi thêm, không đè kết quả AI. `spot_code` lấy từ cấu hình backend để hiển thị.
5. Backend tính summary từ **nhãn cuối**, có đếm UNKNOWN. `processing_time_ms` chỉ đo bên trong handler AI, không gồm độ trễ mạng/backend.

Ví dụ client để Nam tham khảo; đây **chưa phải adapter đã commit**:

```python
import json
import httpx

def call_ai(base_url, camera_id, spots, image_bytes):
    payload = [
        {"spot_id": str(spot["id"]),
         "polygon": [[point["x"], point["y"]] for point in spot["polygon"]]}
        for spot in spots
    ]
    with httpx.Client(timeout=httpx.Timeout(10.0, connect=2.0)) as client:
        response = client.post(
            base_url.rstrip("/") + "/v1/infer",
            data={"camera_id": str(camera_id), "spots_json": json.dumps(payload)},
            files={"image": ("snapshot.jpg", image_bytes, "image/jpeg")},
        )
    response.raise_for_status()
    result = response.json()
    if result["camera_id"] != str(camera_id) or [p["spot_id"] for p in result["predictions"]] != [p["spot_id"] for p in payload]:
        raise ValueError("AI response does not match snapshot spots")
    return result  # Kiểm tiếp schema trước khi ghi database một lần.
```

Timeout 10 giây chỉ là giá trị bắt đầu cho demo, chưa được đo thành SLO. Cần giới hạn retry 503/timeout với backoff trên **cùng job** và bảo đảm idempotency; 413/415/422 không nên retry nguyên request. 500 hoặc response sai cần log mã lỗi/job ID và đánh dấu job failed, giữ snapshot hoàn tất trước đó. `/health` báo tiến trình; `/ready=200` mới báo model sẵn sàng. AI chưa xác thực người gọi, cần chạy trong mạng riêng.

## Kiểm thử và quyết định cần Nam review

- Với checkpoint rc2 thật: gửi 37 polygon khác nhau, kiểm đủ 37 ID/thứ tự, model version và threshold; thử UNKNOWN trên mẫu validation, polygon sai/422, model thiếu/503, timeout, response thiếu, spot ID trùng.
- Kiểm chuỗi snapshot → job → prediction lưu → history/summary → frontend; cả lúc camera config đổi trong khi job chạy, retry, stale và nhãn review. Mock không được gọi là inference thật.
- Thống nhất sửa `/predict` thành `/v1/infer` trong contract backend, cách khóa phiên bản cấu hình, trường lưu thêm, timeout, bảo mật và bàn giao gói. Chỉ cập nhật tài liệu backend trong PR của Nam sau khi thống nhất.

ZIP rc2 không nằm trong Git. Khang cần chuyển gói qua kênh nội bộ; Nam kiểm SHA-256 ZIP `6073421790203b850f71e6b013ad49a2ae3b42417ec00ec08236483a1603b27a`, giải nén và chạy `verify_release.py` trước khi khởi động. Xem [hướng dẫn release](RELEASE_README.md) và [bàn giao backend](BACKEND_HANDOVER.md). Frontend nhận nhãn cuối qua backend; unavailable/stale là trạng thái khác với UNKNOWN.
