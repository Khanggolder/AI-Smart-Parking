# Thử nghiệm trích frame MP4 bằng trình duyệt

## Phạm vi

Trang thử nghiệm `/dev/video-frame` chỉ có trong Vite development. Người dùng chọn một file MP4 trên máy, phát hoặc tua video, chụp frame đang hiển thị bằng Canvas và tải ảnh JPEG về. Video được đọc trong trình duyệt; trang thử nghiệm không tự tải video hay ảnh lên backend.

Không cần FFmpeg để chạy tính năng trên trình duyệt. Định dạng MP4 là một container; video chỉ phát được nếu codec của nó được trình duyệt hỗ trợ.

## Kết quả kiểm tra

- Một MP4 tổng hợp H.264, 320 × 240, thời lượng 2 giây đã được mở trong trình duyệt thử nghiệm.
- Chụp frame tại 0 giây và cuối video thành công; trang hiển thị ảnh JPEG và giữ kích thước 320 × 240.
- Lint, build và các test frontend hiện có pass.
- Kiểm thử thủ công với video mẫu carPark: bản MP4 dùng HEVC không hiển thị hình trên trình duyệt được thử; bản chuyển sang H.264 phát được và trích, tải JPEG 1100 × 720 thành công.
- Frame JPEG được gửi thủ công qua Dashboard và xử lý thành công: 8 ô gồm 2 trống, 3 có xe và 3 chưa xác định. Kết quả này chứng minh luồng tích hợp hoạt động, chưa đánh giá được độ chính xác tổng quát của model.
- Chưa kiểm tra với video camera của nhóm, nhiều trình duyệt hoặc video dung lượng lớn.

## Kết nối với hệ thống hiện tại

Backend hiện nhận ảnh JPEG/PNG qua API snapshot, không nhận video. Người dùng có thể tải JPEG từ trang thử nghiệm rồi chọn ảnh đó ở Dashboard. Frame phải có cùng kích thước và góc nhìn với ảnh tham chiếu của camera; cùng độ phân giải chưa đủ để bảo đảm polygon khớp. Gửi ảnh đến Dashboard tạo snapshot được lưu trong lịch sử.

Vị trí `currentTime` chỉ là số giây trong video, không phải thời gian chụp thực tế. Nếu biết thời điểm bắt đầu ghi, thời gian của frame có thể được tính bằng thời điểm bắt đầu cộng vị trí trong video. Nếu không biết, không nên gán thời gian hiện tại thành thời gian chụp thật hoặc diễn giải video cũ là dữ liệu trực tiếp.

## Hướng mở rộng sau thử nghiệm

- Thủ công: chọn camera và frame, xác nhận thời gian chụp thực tế, kích thước, rồi gửi ảnh đến API snapshot hiện có và hiển thị kết quả job.
- Theo chu kỳ: chỉ gửi frame tiếp theo khi job trước đã hoàn tất; có nút dừng, xử lý lỗi/timeout, tốc độ phân tích hữu hạn và không tạo đồng thời nhiều job. Cần đánh giá số snapshot và dung lượng lưu trữ.
- Không dùng polygon của camera này cho video góc camera khác. Với góc thay đổi, cần cấu hình ảnh và polygon tương ứng.
- Trước khi chọn tự động, nhóm cần thống nhất thời điểm bắt đầu video, tần suất, chính sách lưu, trường hợp tab nền/trình duyệt bị đóng và giới hạn tải AI/backend.

Tham khảo: [Canvas drawImage](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/drawImage), [Canvas toBlob](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toBlob), [videoWidth](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/videoWidth).
