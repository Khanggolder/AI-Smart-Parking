# Model card — AI Smart Parking v0.1.0-rc2

## Mô hình và phạm vi

MobileNetV3-Small với backbone pretrained, classifier hai lớp `empty=0`, `occupied=1`. Checkpoint chọn ở epoch 2, SHA-256 `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`. API trả `model_version=mobilenetv3-small-w2-488ed38efe01`. Đây là **release candidate**, threshold có trạng thái `candidate_not_production_validated`.

Mục đích: MVP giám sát ô đỗ từ camera cố định với polygon đã cấu hình và được kiểm tra trên cùng góc nhìn. Không dùng cho quyết định an toàn quan trọng, nhận diện biển số, tracking, phân loại chắc chắn tuyệt đối hoặc camera mới chưa đánh giá.

## Dữ liệu và tiền xử lý

Nguồn MetaPKLot/PKLot, camera UFPR04. Chia theo **ngày**, không dùng chung ngày/ảnh nguồn/crop giữa train, validation và test: train 2.900 crop/8 ngày (1.724 empty, 1.176 occupied), validation 720/2 ngày (348 empty, 372 occupied), test 740/2 ngày (464 empty, 276 occupied). Dữ liệu test gồm hai ngày nắng; một ngày chỉ có nhãn empty. Annotation ID từ bộ dữ liệu không phải spot ID ổn định cho bãi đỗ thực tế.

Ảnh JPEG/PNG được OpenCV giải mã BGR. Polygon normalized `[0,1]` ánh xạ lên `0..width-1` và `0..height-1`, làm tròn pixel. Vùng ngoài polygon được mask màu 114; lấy bounding box, letterbox 224×224, chuyển RGB, `ToTensor`, chuẩn hóa ImageNet mean `[0.485,0.456,0.406]`, std `[0.229,0.224,0.225]`. W1 lưu crop JPEG; W4 xử lý trực tiếp trong bộ nhớ.

## Kết quả đo

Validation ở checkpoint epoch 2: accuracy và macro-F1 720/720 = 100%. Đây là tập dùng chọn checkpoint và khảo sát threshold, không phải phép đo độc lập cuối.

W5 chạy đúng một lượt trên 740 crop test độc lập theo ngày. Raw accuracy 725/740 = 97,973%; macro-F1 97,835%; occupied precision 97,112%, recall 97,464%, F1 **97,288%**. Ma trận nhầm lẫn (hàng nhãn thật, cột dự đoán empty/occupied): `[[456,8],[7,269]]`. Có 7 false empty và 8 false occupied.

Ngưỡng UNKNOWN cố định từ W3 là 0,90: nếu `max(softmax) < 0,90` thì `label=unknown`, còn `raw_label` và scores vẫn được trả. W5 chấp nhận 712/740, coverage 96,216%; UNKNOWN 28/740. Độ chính xác trong 712 mẫu được chấp nhận là 710/712 = 99,719%. Ma trận có UNKNOWN (hàng thật empty/occupied; cột empty/occupied/unknown): `[[443,0,21],[2,267,7]]`. **Hai occupied bị chấp nhận thành empty** ở confidence 0,9253 và 0,9497. Max-softmax không phải xác suất đúng đã hiệu chuẩn; không dùng 99,719% để che việc từ chối 28 mẫu.

## Hạn chế đã quan sát và chưa đánh giá

Gallery W5 cho thấy crop tối, tán cây và bóng đổ trong nhiều trường hợp khó; đây là mô tả thị giác, chưa có nhãn nguyên nhân. Biến đổi synthetic trên validation làm giảm accuracy ở trường hợp bóng trái và che giữa; không đại diện cho camera thật. Trong 100 validation crop so W1 JPEG với W4 crop trực tiếp, có một raw label khác nhau nhưng cả hai final label là UNKNOWN. Cần giữ nguyên phiên bản preprocessing này.

**Chưa đánh giá:** camera/góc nhìn khác, mưa, đêm, đỗ lệch, vật trong ô trống, full false-alarm rate trên snapshot hoàn chỉnh có stable spot ID, và latency của 100 polygon thật khác nhau. Không suy ra đủ tin cậy production từ tập UFPR04 này. Hai false empty được chấp nhận là rủi ro cần đưa vào demo và trao đổi với backend.

## Khả năng tái lập

Python 3.11.0, PyTorch `2.11.0+cu128`, torchvision `0.26.0+cu128`, NVIDIA RTX 3050 Laptop GPU; benchmark W5 cũng chạy CPU Intel64 Family 6 Model 154 Stepping 3. Package W7 có source inference, checkpoint, cấu hình và dependency pin. Hash manifest: train `4835afb024738106588075d771bf59acdd006ffe798d9705a74a39004a7c506b`, validation `7316e508ae876e275c4a6276e6e34b3670b74e7ca307b74871655f27d8651ecc`, test `684b8a49e82b7e2c2a9b22f4d97d1ca85c663a26e4e2fbacc69ddabed2cb4e9b`. Raw dữ liệu không nằm trong release.

Nguồn chứng cứ: `reports/w3_confidence_analysis.md`, `reports/w4_inference_report.md`, `reports/w5_evaluation_report.md`, `reports/w5_benchmark_report.md`; W5 JSON/CSV nằm trong `runs/mobilenetv3_gpu/w5_evaluation/` và không được đóng gói/phát lại. W7 chỉ tách model/device helpers khỏi training utilities; regression response 37 polygon trước/sau được so sánh trong `reports/w7_verification_report.md` của repo nguồn.
