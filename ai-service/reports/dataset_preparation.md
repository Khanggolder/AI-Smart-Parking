# W1 – Chuẩn bị dữ liệu UFPR04

- Crop theo `mask` polygon, lấy bounding box và letterbox về 224×224.
- Seed `42`; chọn tối đa `10` ảnh nguồn mỗi ngày.
- Chia train/validation/test theo **ngày**; không có ngày hoặc ảnh toàn cảnh chung giữa các tập.
- Đây là dữ liệu chuẩn bị để huấn luyện, chưa phải kết quả benchmark model.
- `annotation_id` thuộc dữ liệu nguồn, không phải `spot_id` ổn định khi triển khai.
- Nếu mở rộng tập huấn luyện, cần tăng ngày/ảnh và kiểm lại phân bố các tập.

| Tập | Ngày | Ảnh toàn cảnh | Trống | Có xe | Crop |
|---|---:|---:|---:|---:|---:|
| train | 8 | 80 | 1724 | 1176 | 2900 |
| val | 2 | 20 | 348 | 372 | 720 |
| test | 2 | 20 | 464 | 276 | 740 |

## Mẫu bỏ qua và bất thường

- `invalid_contour`: 0

## Nguồn dữ liệu

- MetaPKLot: https://github.com/DSBD-Research/MetaPKLot-Dataset
- Ảnh PKLot có giấy phép CC BY 4.0; cần ghi nguồn và kiểm điều kiện phân phối sản phẩm dẫn xuất.
