# Thử nghiệm trích frame MP4 bằng trình duyệt

## Phạm vi

Trang `/video-monitoring` yêu cầu đăng nhập và hiển thị trong giao diện chính; `/dev/video-frame` tiếp tục dùng để thử nghiệm local. Người dùng chọn một file MP4 trên máy, phát hoặc tua video, chụp frame bằng Canvas và tải ảnh JPEG về. Có thể gửi một frame hoặc gửi theo chu kỳ tới API snapshot hiện có; file video không được tải lên Backend.

Không cần FFmpeg để chạy tính năng trên trình duyệt. Định dạng MP4 là một container; video chỉ phát được nếu codec của nó được trình duyệt hỗ trợ.

## Video kiểm thử

File [carPark-h264.mp4](fixtures/carPark-h264.mp4) là bản chuyển mã H.264 từ [carPark.mp4 của dự án car-parking-detection](https://github.com/harshbafnaa/car-parking-detection/blob/main/carPark.mp4). File dài khoảng 28 giây, kích thước 1100 × 720 px; video được sử dụng làm mẫu thử cho nhóm. Thời gian ghi gốc chưa xác định: chỉ dùng camera và database thử nghiệm khi nhập thời gian giả lập, không coi kết quả là dữ liệu giám sát thực tế.

Để thử mẫu này: chạy Vite, mở `/dev/video-frame`, tạo camera thử bằng frame từ chính video làm ảnh tham chiếu, vẽ polygon và chọn camera đó. Nếu nhập thời gian giả lập, chỉ dùng database thử vì Backend chưa đánh dấu dữ liệu giả lập. Thử phân tích một frame, phân tích theo chu kỳ, nút dừng và đối chiếu Lịch sử. Với `/video-monitoring`, dùng video biết thời gian ghi thực tế.

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

## Thử nghiệm theo chu kỳ

Đăng nhập trước, chọn camera và video có cùng góc nhìn, kích thước; nhập thời gian bắt đầu ghi video thực tế tại vị trí 0 giây và xác nhận dữ liệu sẽ được lưu. Không dùng thời gian giả lập trong giao diện chính: snapshot trong database không có cờ phân biệt dữ liệu thử. Chức năng kiểm tra kích thước và từ chối thời gian chụp quá xa trong tương lai, nhưng không thể tự xác minh thời gian hoặc góc quay. Chế độ chu kỳ giới hạn 1–10 frame mỗi lần và chờ 5–300 giây sau khi job trước hoàn thành; không bảo đảm khoảng cách cố định theo thời gian video. Chạy video rồi bắt đầu; tạm dừng video hoặc bấm Dừng sẽ ngừng gửi frame mới. Snapshot đã gửi vẫn tiếp tục xử lý. Phân tích thủ công một frame có thể thực hiện khi video đang tạm dừng.

Nếu mạng lỗi hoặc job quá hạn khiến không xác định được kết quả, chức năng ngừng và khóa chạy lại trong cùng tab, kể cả khi tải lại trang. Kiểm tra Lịch sử, chờ job hoàn tất rồi xác nhận mở khóa để tiếp tục. Rời trang không hủy job đã gửi; khóa theo tab không ngăn thao tác từ tab hoặc thiết bị khác.

Kiểm thử thủ công được người dùng báo thành công với ba frame ở khoảng giây 12, 21 và 32, cùng Lịch sử và thao tác dừng. Các thành viên khác cần thử lại trong môi trường của mình.

Kiểm tra bổ sung: test Backend dùng SQLite trong bộ nhớ và AI giả lập cho các trường hợp AI trả 503/422/500 hoặc quá thời gian; bốn trường hợp pass. Test FE giả lập job thất bại, mất kết nối khi kiểm tra job, quá thời gian, dừng trong khoảng chờ và quy đổi thời gian frame; pass. Các test giả lập này không chứng minh hành vi khi đóng hoặc chuyển tab thực tế trong từng trình duyệt. Thời gian do người dùng nhập không được xác minh tự động, và Backend chưa lưu cờ phân biệt video thử.

## Hướng mở rộng sau thử nghiệm

- Thủ công: chọn camera và frame, xác nhận thời gian chụp thực tế, kích thước, rồi gửi ảnh đến API snapshot hiện có và hiển thị kết quả job.
- Theo chu kỳ: chỉ gửi frame tiếp theo khi job trước đã hoàn tất; có nút dừng, xử lý lỗi/timeout, tốc độ phân tích hữu hạn và không tạo đồng thời nhiều job. Cần đánh giá số snapshot và dung lượng lưu trữ.
- Không dùng polygon của camera này cho video góc camera khác. Với góc thay đổi, cần cấu hình ảnh và polygon tương ứng.
- Trước khi chọn tự động, nhóm cần thống nhất thời điểm bắt đầu video, tần suất, chính sách lưu, trường hợp tab nền/trình duyệt bị đóng và giới hạn tải AI/backend.

Tham khảo: [Canvas drawImage](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/drawImage), [Canvas toBlob](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toBlob), [videoWidth](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/videoWidth).
