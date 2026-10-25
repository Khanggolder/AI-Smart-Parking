# W5 – Đánh giá trên tập test độc lập

## Quy trình và nguồn kết quả

Trước khi đọc ảnh test, W5 khóa checkpoint W2, ngưỡng W3, manifest và cách đánh giá trong `runs/mobilenetv3_gpu/w5_evaluation/frozen_evaluation_config.json`. SHA-256 checkpoint: `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`; test manifest: `684b8a49e82b7e2c2a9b22f4d97d1ca85c663a26e4e2fbacc69ddabed2cb4e9b`. Checkpoint ghi cùng hash train/validation/test; kiểm tra không thấy ngày, ảnh nguồn hoặc crop trùng giữa các tập. Class order là `empty`, `occupied`; ngưỡng là **0,90**.

Chỉ có **một lượt test chính thức** trên 740 crop JPEG W1 đã lưu, dùng transform validation (RGB, 224×224, chuẩn hóa ImageNet), `eval()` và `torch.inference_mode()`. Nhãn thật chỉ dùng tính metric, không truyền vào `ModelLoader.predict`. Script từ chối ghi đè kết quả chính thức hoặc chạy lượt thứ hai. File chi tiết `test_predictions.csv`, `test_metrics.json`, `unknown_metrics.json`, `test_confusion_matrix.png`, `error_analysis.json`, `error_gallery.jpg` nằm trong `runs/` bị Git ignore.

## Bộ phân loại hai lớp, trước ngưỡng UNKNOWN

| Chỉ số | Kết quả |
|---|---:|
| Số crop | 740 |
| Accuracy | 97,973% (725/740) |
| Macro precision | 97,800% |
| Macro recall | 97,870% |
| Macro F1 | 97,835% |
| Empty precision / recall / F1 | 98,488% / 98,276% / 98,382% |
| Occupied precision / recall / F1 | 97,112% / 97,464% / **97,288%** |

Ma trận nhầm lẫn, hàng là nhãn thật và cột là dự đoán:

| Nhãn thật | Empty | Occupied |
|---|---:|---:|
| Empty | 456 | 8 |
| Occupied | 7 | 269 |

Có 7 false empty và 8 false occupied. Mục tiêu NFR-01, occupied-F1 ≥ 0,90, đạt trên **tập test UFPR04 tách theo ngày** (`0,972875`); không suy ra chất lượng trên camera hoặc thời tiết khác. Ngày 2012-12-21 có 370 crop (94 empty, 276 occupied), accuracy 97,568%, macro-F1 96,846%. Ngày 2012-12-24 có 370 crop **đều empty**, accuracy 98,378%, 6 false occupied. Helper trả occupied-F1 bằng 0 khi không có occupied thật; macro-F1 49,591% của ngày này không thể diễn giải là chất lượng nhận occupied. Cả hai ngày đều nắng.

## Sau ngưỡng UNKNOWN 0,90

| Chỉ số | Kết quả |
|---|---:|
| Được chấp nhận | 712 |
| UNKNOWN | 28 (21 empty thật, 7 occupied thật) |
| Coverage / tỷ lệ UNKNOWN | 96,216% / 3,784% |
| Accuracy phần được chấp nhận | 99,719% (710/712) |
| Lỗi vẫn được chấp nhận | 2 (0,281% của phần chấp nhận; 0,270% toàn bộ) |
| Empty recall, tính UNKNOWN là bỏ sót | 95,474% |
| Occupied recall, tính UNKNOWN là bỏ sót | 96,739% |

Ma trận hàng nhãn thật, cột nhãn cuối:

| Nhãn thật | Empty | Occupied | UNKNOWN |
|---|---:|---:|---:|
| Empty | 443 | 0 | 21 |
| Occupied | 2 | 267 | 7 |

Trong 15 lỗi raw, ngưỡng từ chối 13 và **vẫn chấp nhận 2 false empty** (2/15 = 13,333% lỗi raw). Hai confidence là 0,925317 và 0,949709. Điểm max-softmax chưa được hiệu chuẩn thành xác suất đúng. Chỉ nêu accuracy 710/712 sẽ che 28 mẫu bị từ chối và phần recall giảm.

## Phân tích lỗi và trường hợp khó

`error_analysis.json` ghi 15 lỗi raw cùng đường dẫn crop, ngày, camera, nhãn thật/dự đoán, confidence và UNKNOWN; `error_gallery.jpg` gồm false empty, false occupied, UNKNOWN, điểm thấp và lỗi được chấp nhận. Có crop tối, cây và bóng đổ, xe khó thấy trong polygon. Đây là quan sát trực quan, chưa phải nhãn nguyên nhân. Hai false empty được chấp nhận đều ngày 2012-12-21 (confidence 0,9253 và 0,9497).

Phép thử sau dùng biến đổi xác định **trong bộ nhớ** trên 720 JPEG validation; không đổi ảnh gốc, checkpoint hoặc threshold. Nó đo độ nhạy, không đo camera thật:

| Tình huống | Raw accuracy | UNKNOWN | Lỗi được chấp nhận |
|---|---:|---:|---:|
| Validation gốc | 100,000% | 0,833% | 0 |
| Giảm sáng tổng hợp ×0,5 | 99,306% | 1,389% | 1 |
| Giảm tương phản ×0,5 | 100,000% | 0,972% | 0 |
| Bóng tổng hợp nửa trái | 96,667% | 7,639% | 3 |
| Che giữa ảnh 35% | 98,472% | 3,056% | 3 |

Số liệu gốc ở `hard_cases_synthetic_val.json`. Không có tập thật có nhãn riêng cho đỗ lệch, vật trong ô trống, góc camera khác hay từng loại bóng/cây. Gallery chỉ là bằng chứng định tính.

## So crop JPEG W1 với crop trong bộ nhớ W4

So 100 hàng validation cách đều, dùng cùng polygon annotation và chuyển normalized → pixel. Cả 100 mảng tọa độ khớp. Sai khác pixel trung bình 0,399 đơn vị màu; chênh lệch kênh lớn nhất 39. Chênh confidence trung bình 0,00238, lớn nhất 0,23094. **Một raw label đổi, không có final label đổi**, vì cả hai cách đều trả UNKNOWN cho crop `2012-12-18/7546449674bc21.jpg`: W1 raw empty ở 0,7384, W4 raw occupied ở 0,5074. Sai khác pixel trung bình nhỏ vẫn có thể ảnh hưởng quyết định gần ranh giới. Chi tiết ở `preprocessing_consistency_val.json`; W5 không sửa preprocessing theo kết quả test.

## Giới hạn FULL và bàn giao

**Tỷ lệ báo FULL sai: chưa đánh giá vì thiếu nhãn snapshot toàn bãi.** Manifest test có 20 ảnh, mỗi ảnh 37 crop được chọn; annotation ID phụ thuộc ảnh, không chứng minh 37 ID ô vật lý ổn định hoặc toàn bộ ô của bãi. Không được lấy chúng để dựng một kết quả FULL giả. FULL thuộc backend: chỉ kết luận khi mọi ô hợp lệ đều occupied; ô empty hoặc UNKNOWN cản kết luận chắc chắn.

Ngưỡng vẫn có trạng thái `candidate_not_production_validated`. Trước triển khai cần ảnh khó có nhãn từ camera đích, snapshot toàn bãi với spot ID ổn định, các camera/thời tiết khác. Nếu đổi model, preprocessing hoặc threshold, phải chọn trên dữ liệu phát triển mới và dành tập test độc lập mới; W5 đã được mở xem. Khi bàn giao cho Nam, cần giữ JSON/CSV/gallery W5 và hash model.
