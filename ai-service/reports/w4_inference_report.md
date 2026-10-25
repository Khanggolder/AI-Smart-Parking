# W4 inference service report

## Bằng chứng triển khai

- Model: MobileNetV3-Small W2 `best.pt`, pretrained backbone, epoch 2; checkpoint SHA-256 `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada` khớp W3 config. Không tải lại pretrained weights, không retrain. Class order `empty=0`, `occupied=1`, input RGB 224×224, ImageNet normalization.
- Preprocessing dùng chung `src/w1_crop.py` với W1: OpenCV BGR, polygon mask màu 114 bên ngoài, bbox, letterbox 224×224. Sau đó chuyển RGB, transform validation `Resize`, `ToTensor`, `Normalize`. W1 crop được lưu JPEG nên ảnh đi qua file JPEG trong W1 có sai biệt nén nhỏ so với crop inference trong bộ nhớ; toán tử crop và tensor transform giống nhau.
- Ngưỡng 0.90 lấy từ W3 `threshold_candidate.json`, rule `max_softmax < threshold`. Cấu hình W3 đánh dấu `candidate_not_production_validated`.
- `GET /health`, `GET /ready`, `POST /v1/infer` đã có. Model load một lần trong lifespan; request theo batch tối đa 32 tensor, giữ thứ tự ID, không đọc nhãn hoặc ghi database.

## Smoke thực tế

Lệnh `python ai-service/scripts/smoke_inference.py` dùng FastAPI TestClient và checkpoint thật trên CUDA, ảnh UFPR04 validation `2012-12-18_10_40_06.jpg` kích thước 1280×720, 366385 bytes. Request gồm 37 polygon và các ID thử nghiệm `DEMO-xxx`. `/ready` báo CUDA; `/v1/infer` trả 200, model version `mobilenetv3-small-w2-488ed38efe01`, threshold 0.90, 37 predictions đúng thứ tự. Ở lượt cuối, handler mất 509.47 ms và trả 37 nhãn `occupied`. Năm kết quả đầu đều có `raw_label=occupied`, `label=occupied`, `confidence=1.0` theo giá trị float32; score empty vẫn được trả về (cỡ 1e-10 đến 1e-9). Đây là inference quan sát được, không phải phép đánh giá accuracy.

Ngoài TestClient, Uvicorn chạy thật tại `127.0.0.1:8001`: HTTP `GET /health` và `GET /ready` đều trả 200; HTTP multipart `POST /v1/infer` với một polygon trên ảnh trên trả 200, `spot_id=DEMO-001`, `label=occupied`, `processing_time_ms=378.116` ở lượt này. Server đã được dừng sau kiểm tra.

## Unit và API tests

`python -m pytest ai-service/tests -q`: **31 passed** sau cập nhật cuối. Bao gồm checkpoint thật trên CPU và CUDA, hash không khớp, class/score, polygon normalized, mask/resize/normalization so với W1, ảnh lỗi, duplicate ID, 100-spot cap, thứ tự batch, UNKNOWN, health/ready, multipart, lỗi model và inference. Không dùng test split.

## Benchmark

Nguồn: cùng ảnh validation 1280×720; Intel64 Family 6 Model 154 Stepping 3 và NVIDIA GeForce RTX 3050 Laptop GPU; PyTorch 2.11.0+cu128; batch size 32. Mỗi case 3 warm-up và 10 lượt đo, chạy GPU rồi CPU **tuần tự**. GPU đồng bộ ở thời điểm lấy tensor về CPU và tại ranh giới đo. Các số dưới là mili giây, làm tròn 1 chữ số. `Pre p50` gồm decode ảnh, validate, crop và tensor; `Model p50` gồm batch inference và chuyển scores về CPU; `Total` gồm hai bước và dựng output. Các p50 thành phần không nhất thiết cộng bằng p50 tổng. Chưa gồm network, upload HTTP, xếp hàng, hay tải đồng thời.

| Device | Spots | Pre p50 | Model p50 | Total p50 | Total p95 | Peak GPU allocated |
|---|---:|---:|---:|---:|---:|---:|
| CUDA | 1 | 9.5 | 8.4 | 18.1 | 19.2 | 18.4 MB |
| CUDA | 10 | 19.8 | 10.1 | 31.0 | 34.1 | 41.8 MB |
| CUDA | 50 | 58.7 | 30.0 | 90.8 | 98.1 | 100.2 MB |
| CUDA | 100 | 105.5 | 63.9 | 173.9 | 181.3 | 100.2 MB |
| CPU | 1 | 8.7 | 8.9 | 18.0 | 19.4 | — |
| CPU | 10 | 18.5 | 21.4 | 40.7 | 57.7 | — |
| CPU | 50 | 56.4 | 89.2 | 146.7 | 152.9 | — |
| CPU | 100 | 92.5 | 186.6 | 287.0 | 364.5 | — |

Raw JSON: `ai-service/runs/mobilenetv3_gpu/w4_benchmark_cuda.json` và `_cpu.json` (ignored by Git). Ảnh nguồn chỉ có 37 polygon, vì vậy tải 50/100 lặp các polygon hợp lệ với ID benchmark khác nhau. Kết quả này cho thấy engine local ở tải thử dưới 15 giây, nhưng **chưa đủ để tuyên bố NFR-02** cho đường đi production 100 ô thực, HTTP, truy cập đồng thời và điều kiện camera triển khai.

## Giới hạn và phối hợp

- Ngưỡng W3 chưa xác thực production; thử nghiệm che khuất W3 có 3 dự đoán sai vẫn được chấp nhận. Backend không nên tự biến `unknown` thành `empty`.
- Camera thay đổi góc nhìn khiến polygon cũ có thể sai; cần quản lý phiên bản polygon/camera ở backend. Service chỉ kiểm tra hình học và tọa độ.
- Backend cần thống nhất quy ước normalized `[0,1]` → pixel `0..width-1`/`0..height-1`, IDs, timeout/retry, 503, xác thực kết nối và lưu `model_version`. Frontend giữ vai trò polygon editor và dashboard.
- Chưa thấy API contract backend riêng trong repository; đối chiếu [AI_API_CONTRACT.md](../docs/AI_API_CONTRACT.md) trước khi kết nối.
