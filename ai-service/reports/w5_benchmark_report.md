# W5 – Đo thời gian xử lý AI qua engine và HTTP

## Dữ liệu và cách đo

Một snapshot validation UFPR04 JPEG 1280×720 có **37 polygon khác nhau**. Các trường hợp 1, 10, 37 ô dùng polygon thật khác nhau. Trường hợp 50 và 100 ô **lặp polygon** với benchmark ID riêng, chỉ là tải tổng hợp; không phải 50/100 ô vật lý độc lập. Không gửi nhãn thật cho engine.

Máy đo: CPU Intel64 Family 6 Model 154 Stepping 3, GPU NVIDIA RTX 3050 Laptop; Python 3.11, PyTorch 2.11.0+cu128, torchvision 0.26.0+cu128, batch 32. GPU và CPU được đo lần lượt. Mỗi thiết bị và mỗi số ô có **5 lượt warm-up, 50 lượt đo** cho engine trong tiến trình và cho endpoint Uvicorn multipart trên localhost. CUDA đồng bộ khi chuyển output về CPU và tại mốc đo engine.

Thời gian HTTP phía client dùng kết nối giữ lại; gồm tạo request, truyền localhost, xử lý server và nhận response. Không gồm frontend, backend, mạng xa, database hoặc camera chụp ảnh. `pre` gồm giải mã, validate, polygon crop W1 và tạo tensor. `model` gồm batch forward, softmax và chuyển kết quả về CPU. Các p50 thành phần không nhất thiết cộng bằng p50 tổng.

## Độ trễ (ms)

| Thiết bị | Ô | Loại tải | Pre p50 | Model p50 | Engine p50 / p95 | HTTP p50 / p95 |
|---|---:|---|---:|---:|---:|---:|
| CUDA | 1 | khác nhau | 7,0 | 5,5 | 12,8 / 18,0 | 19,0 / 24,7 |
| CUDA | 10 | khác nhau | 14,4 | 7,6 | 22,6 / 30,2 | 33,0 / 39,9 |
| CUDA | 37 | khác nhau | 34,9 | 24,5 | 62,5 / 75,2 | 74,5 / 109,0 |
| CUDA | 50 | lặp polygon | 49,9 | 30,3 | 83,5 / 94,8 | 104,2 / 117,7 |
| CUDA | 100 | lặp polygon | 102,3 | 75,1 | 182,3 / 223,9 | 194,8 / 252,8 |
| CPU | 1 | khác nhau | 8,6 | 9,1 | 17,1 / 18,8 | 19,1 / 23,1 |
| CPU | 10 | khác nhau | 18,3 | 21,4 | 40,0 / 42,7 | 40,9 / 50,2 |
| CPU | 37 | khác nhau | 44,3 | 75,1 | 120,8 / 130,3 | 125,9 / 148,3 |
| CPU | 50 | lặp polygon | 57,3 | 94,1 | 152,2 / 161,0 | 156,3 / 185,5 |
| CPU | 100 | lặp polygon | 105,2 | 194,7 | 303,8 / 330,9 | 324,5 / 356,2 |

PyTorch peak allocated trên GPU sau warm-up: 18,4 MB (1 ô), 41,8 MB (10 ô), 100,2 MB (37/50/100 ô); đây **không phải tổng VRAM**. Tạo `ModelLoader` mất 1467,4 ms CUDA và 108,2 ms CPU trong phép đo này; từ khởi động tiến trình đến `/ready` là 4351,1 và 4922,5 ms. Các số khởi động là một quan sát riêng, không phải p50 và không nằm trong độ trễ request.

## Request đồng thời trên localhost

Gửi 20 request cho **37 polygon khác nhau** bằng 1, 2 hoặc 4 client thread đến một Uvicorn process. Bảng là p95 phía client và throughput đạt được trong 20 request:

| Thiết bị | Thread | p95 ms | Request/s |
|---|---:|---:|---:|
| CUDA | 1 | 150,3 | 10,3 |
| CUDA | 2 | 156,5 | 13,8 |
| CUDA | 4 | 434,3 | 13,3 |
| CPU | 1 | 138,5 | 7,9 |
| CPU | 2 | 276,7 | 8,7 |
| CPU | 4 | 625,4 | 7,6 |

Khi tăng đồng thời có chờ hàng và tranh tài nguyên. Phép thử localhost ngắn này không bảo đảm năng lực triển khai.

## Đọc kết quả theo NFR-02

Với ảnh 1280×720 và **37 ô thật khác nhau**, HTTP p95 là 109,0 ms CUDA và 148,3 ms CPU, dưới mục tiêu 15 giây của SRS **trên máy đo local này**. **100 ô thật khác nhau chưa được đánh giá.** Tải 100 ô lặp polygon cũng dưới 15 giây trong phép đo, nhưng không chứng nhận cho bãi thật, backend hoặc tải đồng thời.

Số đo JSON ở `runs/mobilenetv3_gpu/w5_evaluation/benchmark_cuda.json` và `benchmark_cpu.json` (Git ignore). Lệnh tái lập: `python ai-service/scripts/benchmark_e2e.py --device cuda --runs 50 --warmup 5`; chạy lại với `--device cpu`. Script tự khởi động và dừng Uvicorn.
