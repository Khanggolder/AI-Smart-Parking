# Báo cáo kỹ thuật AI Smart Parking — bản lịch sử v0.1.0-rc1

Đây là báo cáo tại thời điểm W6/rc1. Gói hiện hành là `v0.1.0-rc2`; xem [Model Card](../docs/MODEL_CARD.md) và [Release README](../docs/RELEASE_README.md) cho trạng thái bàn giao hiện tại.

## 1. Bài toán và phạm vi

Phân loại trạng thái `empty`/`occupied` cho từng vùng ô đỗ được định nghĩa bằng polygon trên ảnh từ camera cố định. Service trả thêm `unknown` nếu điểm softmax cao nhất dưới ngưỡng ứng viên. Kết quả dùng cho MVP và demo UFPR04; FULL/STALE và lưu lịch sử thuộc backend. Release chưa được xác nhận production.

## 2. Dữ liệu, annotation và chia tập

Nguồn MetaPKLot/PKLot UFPR04 với annotation polygon. W1 chọn tối đa 10 ảnh mỗi ngày, seed 42; tạo crop bằng mask và bounding box. Mỗi `annotation_id` là ID của dữ liệu nguồn, không phải ID ô đỗ ổn định để tích hợp. Chia theo ngày, kiểm không trùng ngày, ảnh nguồn hoặc crop giữa các tập.

| Tập | Ngày | Ảnh toàn cảnh | Empty | Occupied | Crop |
|---|---:|---:|---:|---:|---:|
| Train | 8 | 80 | 1.724 | 1.176 | 2.900 |
| Validation | 2 | 20 | 348 | 372 | 720 |
| Test | 2 | 20 | 464 | 276 | 740 |

Test chỉ gồm hai ngày nắng; một ngày hoàn toàn empty. Hash SHA-256 train `4835afb024738106588075d771bf59acdd006ffe798d9705a74a39004a7c506b`, validation `7316e508ae876e275c4a6276e6e34b3670b74e7ca307b74871655f27d8651ecc`, test `684b8a49e82b7e2c2a9b22f4d97d1ca85c663a26e4e2fbacc69ddabed2cb4e9b`. Các hash khớp checkpoint và cấu hình đóng băng W5. Nguồn: `reports/dataset_preparation.md`, W5 frozen config.

## 3. Tiền xử lý polygon

Service giải mã JPEG/PNG bằng OpenCV (BGR). Tọa độ `[0,1]` nhân với `width-1,height-1`, làm tròn pixel; kiểm polygon hợp lệ. Ngoài ROI được mask xám 114; lấy bbox, letterbox không méo về 224×224; chuyển RGB, tensor và chuẩn hóa ImageNet. Đây là logic W1 dùng lại trong W4. W1 lưu JPEG của crop, còn W4 giữ crop trong RAM; phép so 100 mẫu validation thấy một raw label thay đổi nhưng cả hai final label là UNKNOWN. Không thay tiền xử lý sau W5. Nguồn: `src/w1_crop.py`, `src/preprocessing.py`, `reports/w5_evaluation_report.md`.

## 4. Mô hình và huấn luyện

MobileNetV3-Small pretrained, classifier hai đầu ra theo thứ tự `empty=0`, `occupied=1`. W2 dùng seed 42, batch 16, head LR 0,001, backbone LR 0,00002, kế hoạch tối đa 20 epoch, patience 4 và chạy 6 epoch. Checkpoint được chọn ở **epoch 2** bằng kết quả validation; SHA-256 `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`. Validation tại checkpoint này có accuracy và macro-F1 100% trên 720 crop; đây không phải phép đo độc lập. Nguồn: `runs/mobilenetv3_gpu/history.json`, `best_val_metrics.json`, metadata checkpoint.

## 5. Đánh giá test độc lập W5

Sau khi khóa model, threshold và manifest, W5 chạy một lượt trên 740 W1 JPEG test crop, không dùng nhãn trong inference. Raw accuracy **725/740 = 97,973%**, macro precision 97,800%, macro recall 97,870%, macro-F1 **97,835%**. Occupied precision 97,112%, recall 97,464%, F1 **97,288%**. Confusion matrix, hàng nhãn thật và cột dự đoán `empty, occupied`: `[[456,8],[7,269]]`. Có 7 false empty và 8 false occupied. NFR-01 (occupied F1 ≥ 0,90) **PASS trên UFPR04 independent day-split test**. Kết quả không chứng minh độ chính xác camera khác hay production.

Ngày 2012-12-21 có 94 empty/276 occupied, accuracy 97,568%; ngày 2012-12-24 có 370 empty, accuracy 98,378%. Không diễn giải occupied F1 của ngày không có occupied. Nguồn: `reports/w5_evaluation_report.md`, `runs/mobilenetv3_gpu/w5_evaluation/test_metrics.json`.

## 6. UNKNOWN và phân tích lỗi

W3 chọn ngưỡng ứng viên 0,90 theo quy tắc `max_softmax_probability < threshold`. W5 chấp nhận 712/740 (coverage 96,216%), 28 UNKNOWN (21 empty thật, 7 occupied thật), accuracy của phần chấp nhận 710/712 = 99,719%. Confusion matrix selective, cột `empty, occupied, unknown`: `[[443,0,21],[2,267,7]]`. **Hai occupied bị chấp nhận thành empty** ở confidence 0,9253 và 0,9497. Vì thế UNKNOWN không loại bỏ tất cả lỗi; max-softmax chưa hiệu chuẩn. Ngưỡng mang trạng thái `candidate_not_production_validated`.

Gallery W5 có nhiều crop tối, cây che và bóng đổ, chỉ là quan sát định tính. Biến đổi synthetic trên validation: bóng phủ nửa trái làm raw accuracy 96,667%, 55 UNKNOWN, 3 lỗi được chấp nhận; che giữa 35% làm raw accuracy 98,472%, 22 UNKNOWN, 3 lỗi được chấp nhận. Không suy các số này thành hiệu năng ảnh thật. Nguồn: `reports/w3_confidence_analysis.md`, `reports/w5_evaluation_report.md`.

## 7. Benchmark và NFR

Máy đo: Intel64 Family 6 Model 154 Stepping 3, NVIDIA GeForce RTX 3050 Laptop GPU, Python 3.11, PyTorch 2.11.0+cu128, torchvision 0.26.0+cu128, batch 32. W5 dùng một ảnh UFPR04 thật 1280×720 với **37 polygon khác nhau**, 5 warmup + 50 lượt đo mỗi case/device, chạy GPU và CPU tuần tự. Engine gồm decode/validation/crop/inference/output; HTTP wall đo multipart qua localhost Uvicorn với connection giữ lại, không gồm camera, backend/database hay mạng từ xa.

| Device | Polygon | Engine p50/p95 ms | HTTP p50/p95 ms |
|---|---:|---:|---:|
| CUDA | 37 thật, khác nhau | 62,5 / 75,2 | 74,5 / 109,0 |
| CPU | 37 thật, khác nhau | 120,8 / 130,3 | 125,9 / 148,3 |
| CUDA | 100 synthetic, lặp polygon | 182,3 / 223,9 | 194,8 / 252,8 |
| CPU | 100 synthetic, lặp polygon | 303,8 / 330,9 | 324,5 / 356,2 |

GPU peak PyTorch allocated ở 37 spot là 100,2 MB (không phải tổng VRAM). Thử 20 request đồng thời ở 37 spot, HTTP p95 CUDA với 1/2/4 thread là 150,3/156,5/434,3 ms; CPU là 138,5/276,7/625,4 ms. Đây là thử nghiệm localhost ngắn, không bảo đảm capacity. **NFR-02 PASS cho demo local 37 spot khác nhau; NOT EVALUATED cho 100 spot thật khác nhau.** Source: `reports/w5_benchmark_report.md` và JSON W5. W6 chỉ smoke lại gói, không benchmark lại vì model/runtime và môi trường không đổi; request W6 cuối cùng với 37 spot mất 487,147 ms handler, không diễn giải là percentile benchmark.

## 8. Inference service và tích hợp

FastAPI nạp checkpoint một lần, xác minh hash và metadata/class order, batch inference theo 32 tensor, trả kết quả cùng thứ tự `spot_id`. `GET /health` báo process; `GET /ready` báo model sẵn sàng và version; `POST /v1/infer` nhận multipart image/camera_id/spots_json. Phiên bản model API `mobilenetv3-small-w2-488ed38efe01`, release `v0.1.0-rc1` là định danh gói. Khi ảnh/polygon không hợp lệ trả lỗi HTTP, không tạo prediction `unknown` giả. Service không đọc ground truth, không lưu database, không xử lý FULL/STALE. Nam lấy snapshot và polygon ổn định, gọi API, xác minh ID/số lượng, lưu kết quả và timestamp; Khôi hiển thị final label theo màu xanh/đỏ/xám. Xem `docs/AI_API_CONTRACT.md`, `docs/BACKEND_HANDOVER.md`, `docs/FRONTEND_HANDOVER.md`.

W6 chạy ZIP đã giải nén trên GPU: hash 20 file xác minh, `/health` và `/ready` 200, HTTP multipart trả 37 kết quả đúng thứ tự; crop validation điểm thấp trả UNKNOWN; polygon sai và ảnh hỏng trả 422. Toàn bộ regression: **34 passed**. Overlay ROI được kiểm bằng mắt trên ảnh UFPR04. Đây là kiểm khả năng chạy gói, không thay thế W5 benchmark hay đánh giá accuracy.

## 9. Giới hạn và hướng phát triển

FULL false-alarm rate **NOT EVALUATED** vì thiếu snapshot toàn bãi có ground truth và stable spot ID. Camera khác, mưa/đêm, ô đỗ lệch, vật trong ô trống, góc nhìn dịch chuyển và 100 polygon thật cũng **NOT EVALUATED**. Cần thu thập trường hợp khó có nhãn từ camera đích, xác nhận cấu hình polygon và timestamp, đo end-to-end backend, đánh giá FULL trên snapshot hoàn chỉnh. Nếu đổi trọng số, threshold hoặc preprocessing, tạo phiên bản mới và tập test độc lập mới; không dùng lại W5 như phép xác nhận cuối. Không push/merge/GitHub release trong W6.
