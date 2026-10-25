# W0 – Kiểm tra dữ liệu MetaPKLot UFPR04

Tạo lúc: 2026-10-24T15:15:30+07:00

- Nguồn: https://github.com/DSBD-Research/MetaPKLot-Dataset
- Tải dữ liệu: https://huggingface.co/datasets/DSBD-Research/MetaPKLot-Dataset
- Gói annotation: `annotations/original/spots/PKLot/ufpr04_spots.tar.xz`
- Ảnh PKLot có giấy phép CC BY 4.0; khi dùng cần ghi nguồn PKLot và MetaPKLot. Thành phần khác có thể có giấy phép riêng.
- ID trên ảnh overlay là `id` của annotation, chưa chắc là `spot_id` cố định của ô đỗ.
- Thiếu annotation ngoài `annotationsRectangle` không có nghĩa ô đó trống.

| Ảnh | image_id | Ô có nhãn | Ô vẽ lên ảnh | Trống | Có xe | Lỗi |
|---|---:|---:|---:|---:|---:|---:|
| `PKLot/UFPR04/Cloudy/2012-12-12/2012-12-12_10_00_05.jpg` | 12000000158 | 37 | 37 | 0 | 37 | 0 |
| `PKLot/UFPR04/Rainy/2012-12-07/2012-12-07_16_42_25.jpg` | 12000000044 | 37 | 37 | 2 | 35 | 0 |
| `PKLot/UFPR04/Sunny/2012-12-07/2012-12-07_17_12_25.jpg` | 12000000021 | 37 | 37 | 1 | 36 | 0 |
| `PKLot/UFPR04/Cloudy/2012-12-12/2012-12-12_10_05_05.jpg` | 12000000117 | 37 | 37 | 0 | 37 | 0 |
| `PKLot/UFPR04/Cloudy/2012-12-12/2012-12-12_10_10_05.jpg` | 12000000104 | 37 | 37 | 0 | 37 | 0 |

## Kiểm tra overlay

### PKLot/UFPR04/Cloudy/2012-12-12/2012-12-12_10_00_05.jpg
Overlay: `sample_overlay.png`
- Kiểm tra tự động không phát hiện lỗi; vẫn cần xem ảnh trực quan.

### PKLot/UFPR04/Rainy/2012-12-07/2012-12-07_16_42_25.jpg
Overlay: `sample_overlay_02.png`
- Kiểm tra tự động không phát hiện lỗi; vẫn cần xem ảnh trực quan.

### PKLot/UFPR04/Sunny/2012-12-07/2012-12-07_17_12_25.jpg
Overlay: `sample_overlay_03.png`
- Kiểm tra tự động không phát hiện lỗi; vẫn cần xem ảnh trực quan.

### PKLot/UFPR04/Cloudy/2012-12-12/2012-12-12_10_05_05.jpg
Overlay: `sample_overlay_04.png`
- Kiểm tra tự động không phát hiện lỗi; vẫn cần xem ảnh trực quan.

### PKLot/UFPR04/Cloudy/2012-12-12/2012-12-12_10_10_05.jpg
Overlay: `sample_overlay_05.png`
- Kiểm tra tự động không phát hiện lỗi; vẫn cần xem ảnh trực quan.
