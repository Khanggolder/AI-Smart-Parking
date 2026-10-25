# W3 – Phân tích confidence trên tập validation

## Cách đo

W3 dùng checkpoint MobileNetV3-Small đã chọn ở W2 để suy luận trên **720 crop validation** UFPR04. Train/validation manifest khớp SHA-256 ghi trong checkpoint; ảnh test độc lập không được dùng để chọn ngưỡng. Hai lớp theo thứ tự `empty=0`, `occupied=1`. Crop W1 dùng polygon mask; đầu vào RGB 224×224 và chuẩn hóa ImageNet. Model chạy CUDA, PyTorch 2.11.0+cu128, batch 16; checkpoint chọn ở epoch 2, SHA-256 `488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada`.

Quy tắc: nếu `max(softmax) < threshold` thì nhãn cuối là `unknown`. Hai điểm softmax chưa được hiệu chuẩn thành xác suất dự đoán đúng. W3 không huấn luyện lại, đổi kiến trúc hoặc sửa crop.

## Kết quả

Model phân loại đúng **720/720** crop validation: 348 empty và 372 occupied. Ở ngưỡng ứng viên **0,90**, có 714 kết quả được chấp nhận, 6 UNKNOWN (2 empty thật, 4 occupied thật); coverage 99,17%. Cả 714 kết quả được chấp nhận đều đúng **trên tập này**. Vì validation không có lỗi raw, không thể dùng tập này đo khả năng ngưỡng loại bỏ lỗi thông thường.

Điểm softmax lớn nhất có min 0,5434, median 1,0000, phân vị 5% là 0,9992. Min của empty thật là 0,7351; occupied thật là 0,5434. ECE mô tả với 10 bin là 0,00264, chưa đủ chứng minh calibration.

| Ngưỡng | Chấp nhận | UNKNOWN | Coverage | UNKNOWN empty / occupied | Accuracy phần chấp nhận |
|---:|---:|---:|---:|---:|---:|
| 0,50 | 720 | 0 | 100,00% | 0 / 0 | 100% |
| 0,70 | 719 | 1 | 99,86% | 0 / 1 | 100% |
| 0,80 | 717 | 3 | 99,58% | 1 / 2 | 100% |
| 0,90 | 714 | 6 | 99,17% | 2 / 4 | 100% |
| 0,95 | 712 | 8 | 98,89% | 3 / 5 | 100% |
| 0,98 | 704 | 16 | 97,78% | 7 / 9 | 100% |
| 0,99 | 702 | 18 | 97,50% | 9 / 9 | 100% |

Chi tiết ma trận nhầm lẫn theo ngưỡng, phân bố điểm và từng crop nằm trong thư mục local `runs/mobilenetv3_gpu/confidence/`: `val_confidence_report.json`, `val_predictions.csv`, `val_confidence_distribution.png`, `lowest_confidence_crops.jpg`, `threshold_candidate.json`. Các artifact này không nằm trong Git.

## Ảnh khó và phép thử tổng hợp

Trong gallery điểm thấp có xe tối màu, xe bị cây che hoặc nằm sát mép crop; crop empty có lá cây hoặc ít mặt đường. Đây là quan sát hình ảnh, chưa xác định nguyên nhân của điểm số và chưa chứng minh hiệu năng ở camera khác.

W3 biến đổi **trong bộ nhớ** 720 crop validation để xem độ nhạy; không sửa ảnh gốc:

| Biến đổi tổng hợp | Raw đúng | UNKNOWN ở 0,90 | Đúng / được chấp nhận |
|---|---:|---:|---:|
| Độ sáng ×0,6 | 719/720 | 8 | 712/712 |
| Tương phản ×0,5 | 720/720 | 7 | 713/713 |
| Che hình chữ nhật giữa ảnh, khoảng 35% | 709/720 | 21 | 696/699 |

Phép che giữa ảnh vẫn để lọt **3 dự đoán sai**. Đây là ảnh nhân tạo, không dùng để suy ra độ chính xác ở điều kiện thật. Chi tiết trong `synthetic_sensitivity_report.json` của run local.

## Ngưỡng bàn giao

`threshold_candidate.json` lưu ngưỡng `0,90`, class order, chuẩn hóa, crop mode, hash checkpoint và epoch; trạng thái là `candidate_not_production_validated`. W4 cần nạp đúng checkpoint/cấu hình, trả raw label, hai scores, confidence và nhãn cuối. Cần thêm ảnh có nhãn từ camera đích, gồm ánh sáng yếu, che khuất, camera dịch và vật trong ô trống, trước khi chọn ngưỡng triển khai. W3 từng chạy 14 test PASS; đây là số liệu lịch sử, không thay cho kết quả kiểm thử hiện tại.
