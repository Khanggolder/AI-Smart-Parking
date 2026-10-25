# Hướng dẫn đọc source AI

Mở [README](../README.md) trước để biết bài toán. Tài liệu này theo **luồng thực thi**: khởi động API → một request → xử lý crop → model → JSON. Phần chuẩn bị dữ liệu và đánh giá ở cuối là các chương trình riêng, không chạy mỗi khi API nhận ảnh. Khi giải thích, mở file ở cột đầu và chỉ vào hàm thật; tên trong ngoặc là điểm cần hiểu khi bị hỏi sâu.

## 1. Khởi động service

Lệnh từ root: `python -m uvicorn src.service:app --app-dir ai-service --host 127.0.0.1 --port 8001`. Python import [`src/service.py`](../src/service.py), dòng `app = create_app()`. `create_app(settings=None, loader_factory=ModelLoader)` đọc [`configs/inference.yaml`](../configs/inference.yaml) qua `Settings.load`, dựng FastAPI và đăng ký endpoint. **Model chưa nạp ở lúc import**; `lifespan` khởi tạo `InferenceEngine(ModelLoader(settings))` khi server bắt đầu. Nếu nạp lỗi, nó giữ `engine=None` và thông báo lỗi để `/ready` trả 503; `/health` vẫn 200 vì tiến trình còn sống.

| File | Vai trò, hàm chính và dữ liệu | Ai gọi; cần hiểu khi vấn đáp |
|---|---|---|
| [`src/service.py`](../src/service.py) | `create_app`, `lifespan`, `health`, `ready`, `infer`, `error`. Nhận multipart; trả JSON/HTTP error. | Uvicorn import `app`; backend gọi endpoint. Phân biệt liveness với model readiness và các lỗi 413/415/422/503/500. |
| [`src/model_loader.py`](../src/model_loader.py) | `Settings.load` đọc YAML/env; `ModelLoader.__init__` kiểm file, SHA-256, metadata, class order, 224, mask, chuẩn hóa, ngưỡng; `predict` nhận tensor `N×3×224×224` và trả `N×2` softmax. | `lifespan` tạo loader; `InferenceEngine.infer` gọi `predict`. Vì sao checkpoint và cấu hình W3 phải khớp; `eval()`, `torch.inference_mode()`. |
| [`src/model_runtime.py`](../src/model_runtime.py) | `create_model(pretrained, freeze_features)` dựng MobileNetV3-Small, thay classifier cuối thành 2 lớp; `select_device` chọn CPU/CUDA. | Loader và các script nghiên cứu dùng chung. Trong serving, `pretrained=False` chỉ tránh tải lại trọng số gốc: learned weights vẫn nạp từ checkpoint. |

## 2. Khi nhận một snapshot

Thứ tự gọi thực tế:

```text
service.create_app.<locals>.infer
  → InferenceEngine.infer
    → validate_spots → decode_image → preprocess
      → polygon_pixels → w1_crop.make_crop → BGR sang RGB → TRANSFORM → torch.stack
    → ModelLoader.predict (từng batch) → confidence_utils.decide
  → service.infer ghép camera_id, model_version, threshold, predictions, processing_time_ms
```

1. **HTTP boundary — [`service.py`](../src/service.py).** `infer(image, camera_id, spots_json)` nhận `UploadFile` và hai form field; kiểm ID 1–128 ký tự, MIME JPEG/PNG, giới hạn byte và JSON. `json.loads` biến chuỗi thành danh sách. FastAPI `RequestValidationError` được đổi thành lỗi 422. `InputError` từ tiền xử lý thành 422; CUDA OOM thành 503; lỗi bất ngờ thành 500. Nó không trả nhãn `unknown` cho request hỏng. Câu hỏi thường gặp: tại sao 503 khi `/health` 200? Vì `/ready` mới phụ thuộc model.
2. **Điều phối — [`inference.py`](../src/inference.py).** `InferenceEngine.infer(image: bytes, spots: object)` kiểm danh sách spot, giải mã ảnh, gọi `preprocess`, tách tensor theo `settings.batch_size` (mặc định 32), gọi `loader.predict`, rồi `zip(..., strict=True)` để ghép điểm với spot theo thứ tự đầu vào. Trả `InferenceResult` gồm predictions và các thời gian nội bộ; service chỉ đưa `predictions` vào JSON và tự đo `processing_time_ms`. Câu hỏi: vì sao giữ thứ tự ID? Để backend kiểm mapping trước khi lưu; không suy ID từ vị trí ảnh.
3. **Ảnh và tọa độ — [`preprocessing.py`](../src/preprocessing.py).** `validate_spots` yêu cầu 1–100 spot, ID không rỗng/không trùng và có polygon. `decode_image` dùng Pillow kiểm định dạng/kích thước rồi OpenCV giải mã **BGR**. `polygon_pixels` yêu cầu 3–50 cặp số hữu hạn trong `[0,1]`, diện tích không suy biến, không trùng điểm sau đổi pixel, không tự cắt và bounding box đủ lớn. Tọa độ được nhân với `width-1,height-1` rồi làm tròn. Câu hỏi: tại sao normalized? Cấu hình tỷ lệ theo ảnh; backend vẫn phải bảo đảm cùng camera/cỡ ảnh và đúng phiên bản polygon.
4. **Crop dùng lại từ W1 — [`w1_crop.py`](../src/w1_crop.py).** `make_crop(img, polygons, size=224, mode="mask")` nhận ảnh BGR/polygon pixel, lấy bounding rectangle, tô phần ngoài polygon trong crop bằng giá trị 114, resize giữ tỷ lệ và letterbox nền 114 về 224×224. `preprocess` gọi hàm này từng ô, rồi `cv2.COLOR_BGR2RGB`, `TRANSFORM` (`Resize`, `ToTensor`, ImageNet mean/std) và `torch.stack`. Câu hỏi: vì sao cả letterbox và `Resize`? `make_crop` đã đưa về 224; transform vẫn bảo đảm kích thước tensor đúng. W1 lưu JPEG, runtime giữ trong RAM; nén JPEG có thể gây sai khác nhỏ.
5. **Model và confidence — [`model_loader.py`](../src/model_loader.py), [`confidence_utils.py`](../src/confidence_utils.py).** `predict` kiểm shape, chạy model ở `inference_mode`, kiểm logits hữu hạn rồi softmax về CPU. `decide(empty, occupied, threshold)` lấy argmax; nếu max score `< threshold` thì `label=unknown`, còn `raw_label` vẫn là nhãn argmax. Nó không nhận ground truth. Câu hỏi: confidence 0,95 có phải chắc đúng 95%? Không; đó là điểm softmax chưa hiệu chuẩn. Threshold bằng đúng 0,90 thì được chấp nhận vì điều kiện là `>=`.

## 3. Đường chuẩn bị dữ liệu và huấn luyện

| Đọc theo thứ tự | Input → output, hàm/lớp chính | Điểm cần hiểu và câu hỏi có thể gặp |
|---|---|---|
| [`scripts/prepare_dataset.py`](../scripts/prepare_dataset.py) | Từ annotation MetaPKLot UFPR04 và ảnh nguồn → crop JPEG, `manifests/train.csv`, `val.csv`, `test.csv`. `collect_records`, `split_days`, `main` gọi `w1_crop.make_crop`; phụ thuộc [`inspect_ufpr04.py`](../scripts/inspect_ufpr04.py) để tải/đọc annotation. | Chia **theo ngày**, seed 42; W1 chọn ảnh giới hạn mỗi ngày. Vì sao không chia crop ngẫu nhiên? Nhiều crop từ cùng ảnh/ngày tương quan, gây rò rỉ thông tin. |
| [`src/dataset.py`](../src/dataset.py) | `ParkingSpotDataset` đọc CSV; `__getitem__` đọc crop JPEG, RGB, transform tensor 224×224; trả tensor và ID nhãn 0/1. Train có flip/jitter; val/test không. | Được train/evaluate/analyze gọi. Phân biệt nhãn ground truth chỉ dùng training/metrics với inference API không đọc nhãn. |
| [`src/baseline_utils.py`](../src/baseline_utils.py) | `assert_safe_splits` kiểm ngày/ảnh/crop không trùng; `metrics_from_predictions` tính confusion matrix, precision/recall/F1; `predict_all` chạy validation. Import model helpers từ `model_runtime.py`. | Script train và evaluate gọi; vì sao phải kiểm hash/split trước đánh giá. |
| [`scripts/train_baseline.py`](../scripts/train_baseline.py) | `main`: seed 42; dataset train/val; `create_model(pretrained=True, freeze_features=True)`; AdamW hai learning rate (head 0,001; backbone 0,00002), `CrossEntropyLoss`; mở backbone từ epoch 3 mặc định; lưu `best.pt` khi validation macro-F1 tăng. | Early stopping mặc định patience 4; checkpoint epoch 2 là **kết quả run đã báo cáo**, không phải hard-code. `--weights none`/`--max-batches` chỉ smoke, không tạo baseline học chuyển giao hợp lệ. Test không tham gia chọn checkpoint. |

## 4. Đánh giá và bằng chứng

| File | Đầu vào → đầu ra; mục đích |
|---|---|
| [`scripts/evaluate_baseline.py`](../scripts/evaluate_baseline.py) | CLI đánh giá checkpoint trên `val` mặc định hoặc `test` khi đã chọn model; kiểm metadata và hash manifest, ghi metric/confusion matrix. Không dùng lại test để chỉnh model. |
| [`scripts/analyze_confidence.py`](../scripts/analyze_confidence.py) | Chạy **validation** để so ngưỡng, xem phân bố điểm và hard cases synthetic; ghi `threshold_candidate.json` W3. `SyntheticValidationDataset` chỉ biến đổi ảnh validation trong RAM. Validation 100% không chứng minh UNKNOWN chặn lỗi. |
| [`scripts/evaluate_independent.py`](../scripts/evaluate_independent.py) | `prepare_protocol` kiểm hash, `freeze` ghi cấu hình bất biến, `evaluate` chạy **một lượt test 740 crop** và từ chối ghi đè output. Tạo raw/selective metrics, predictions, error analysis. Không chạy lại chỉ để thử tài liệu. |
| [`scripts/benchmark_e2e.py`](../scripts/benchmark_e2e.py) | `main` đo in-process và Uvicorn localhost với ảnh UFPR04; `spots_for` dùng 37 polygon thật, 50/100 là workload lặp polygon; warmup 5 và 50 lần đo mặc định. Không bao gồm backend/mạng xa. |

Test trong [`tests/`](../tests/) kiểm từng quy tắc và API. Riêng [`test_w5_evaluation.py`](../tests/test_w5_evaluation.py) đọc checkpoint và file kết quả W5 local để đối chiếu, nên clone GitHub sạch thiếu artifact sẽ lỗi. Số liệu cuối và giới hạn nằm ở [báo cáo cuối](../reports/final_ai_report.md), [W5 evaluation](../reports/w5_evaluation_report.md), [benchmark](../reports/w5_benchmark_report.md). [Reports Index](../reports/INDEX.md) dẫn tới các mốc nghiên cứu. Tự luyện câu hỏi tại [Defense Guide](DEFENSE_GUIDE.md).
