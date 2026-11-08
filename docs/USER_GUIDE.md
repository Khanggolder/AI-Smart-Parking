# Hướng dẫn sử dụng AI Smart Parking

Tài liệu mô tả giao diện hiện có để cấu hình bãi xe, phân tích ảnh và xem lịch sử. Trước khi bắt đầu, người vận hành cần được cấp tài khoản và địa chỉ ứng dụng. Backend, cơ sở dữ liệu và AI service cần được khởi động theo [hướng dẫn triển khai Docker](DOCKER_GUIDE.md) hoặc [hướng dẫn backend](../backend/README.md).

## 1. Đăng nhập

1. Mở địa chỉ frontend trong trình duyệt.
2. Nhập tên đăng nhập và mật khẩu được cấp, rồi chọn **Đăng nhập**.
3. Chọn **Đăng xuất** ở góc trên khi kết thúc.

Admin có thể cấu hình bãi xe, camera và ô đỗ. Admin và Operator có thể xem, gửi ảnh phân tích và xác minh kết quả. Nếu không đăng nhập được, kiểm tra tài khoản và kết nối backend.

## 2. Cấu hình bãi xe và camera (Admin)

1. Vào **Quản lý bãi xe**, tạo bãi xe với tên và mô tả nếu cần.
2. Vào **Camera**, chọn bãi xe và tạo camera tương ứng.
3. Vào **Vẽ ô đỗ**, chọn camera vừa tạo.
4. Chọn ảnh tham chiếu JPEG/PNG và bấm **Upload ảnh lên Backend**.

Ảnh tham chiếu phải thể hiện đúng góc camera cố định được dùng cho các ảnh snapshot sau này. Nếu camera đã có ô hoạt động, hệ thống không cho thay ảnh tham chiếu trực tiếp: cần xử lý các ô cũ và cấu hình lại. Để thử mà không ảnh hưởng cấu hình hiện tại, hãy tạo camera thử riêng.

## 3. Vẽ và lưu ô đỗ (Admin)

1. Trên ảnh tham chiếu, nhấp các điểm bao quanh một ô đỗ; dùng ít nhất ba điểm.
2. Chọn **Hoàn thành polygon**. Hệ thống tự tạo mã ô, ví dụ P01.
3. Bấm **Lưu lên PostgreSQL** và đợi thông báo lưu thành công.
4. Lặp lại cho các ô còn lại. Có thể chọn ô để sửa các đỉnh hoặc ngừng kích hoạt.
5. Tải lại trang và chọn lại camera để kiểm tra các ô vẫn nằm đúng vị trí.

Mỗi polygon phải hợp lệ, không tự cắt và có mã ô riêng trong camera. Chọn mã trong danh sách hoặc nhấp polygon để làm nổi bật ô tương ứng. Dashboard chỉ phân tích các ô đã được cấu hình và đang hoạt động. Mã ô đã ngừng kích hoạt vẫn được giữ cho lịch sử, vì vậy số thứ tự có thể không liên tục.

## 4. Phân tích snapshot

1. Vào **Dashboard**, chọn camera đã cấu hình.
2. Chọn ảnh JPEG/PNG cùng góc camera và cùng chiều rộng, chiều cao với ảnh tham chiếu.
3. Nhập thời gian ảnh được chụp, rồi bấm **Tải ảnh và phân tích**.
4. Đợi trạng thái xử lý hoàn tất. Kiểm tra ảnh, polygon và bảng trạng thái từng ô.

Dashboard hiển thị số ô trống, có xe, chưa xác định và tỷ lệ sử dụng. Màu xanh là trống, đỏ là có xe, xám là chưa xác định; bảng bên dưới cung cấp nhãn bằng chữ. Confidence là điểm của mô hình chưa được hiệu chuẩn, không phải bảo đảm dự đoán đúng.

**FULL** chỉ xuất hiện khi có ô được cấu hình và tất cả nhãn hiện tại đều là có xe; nhãn hiện tại có thể đã được người dùng xác minh. **STALE** cho biết ảnh đã cũ theo ngưỡng của backend. Đây là ảnh chụp tại thời điểm ghi trên màn hình, không phải video trực tiếp.

Nếu ảnh bị từ chối, kiểm tra định dạng, kích thước và camera đã có ảnh tham chiếu cùng polygon hoạt động. Nếu phân tích thất bại, kiểm tra kết nối backend và AI service; kết quả snapshot thành công trước đó được giữ lại.

## 5. Xem lịch sử và tải báo cáo

1. Vào **Lịch sử** để xem danh sách snapshot.
2. Chọn bộ lọc camera, khoảng ngày, trạng thái xử lý hoặc trạng thái ô, rồi bấm **Áp dụng bộ lọc**.
3. Chọn **Xem chi tiết** để xem ảnh và kết quả của snapshot đó. Dùng **Trang trước** / **Trang sau** khi danh sách có nhiều trang.
4. Vào **Báo cáo**, chọn snapshot hoàn thành và bấm **Xem chi tiết**.
5. Bấm **Tải CSV snapshot này** để tải báo cáo của snapshot đang chọn.

**Trạng thái xử lý** lọc job; **Trạng thái ô** tìm snapshot hoàn thành có ít nhất một ô mang nhãn hiện tại đã chọn. Nếu có quá 500 snapshot hoàn thành trong phạm vi tìm kiếm, hãy chọn camera hoặc thu hẹp khoảng ngày. Áp dụng lại bộ lọc sau khi xác minh.

Với snapshot hoàn thành, vào **Lịch sử**, chọn **Xem chi tiết** rồi chọn **Xác minh** tại ô cần kiểm tra. Chọn xác nhận dự đoán AI, hoặc chọn sửa nhãn và nhập lý do; sau đó bấm **Lưu xác minh**. Giao diện giữ nhãn AI ban đầu và hiển thị nhãn hiện tại cùng lịch sử xác minh. Nếu có thông báo xung đột, tải lại lịch sử trước khi thử lại.

## 6. Khi gặp sự cố

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| Không tải được danh sách hoặc ảnh | Kiểm tra backend đang chạy và phiên đăng nhập còn hiệu lực. |
| Không có snapshot phù hợp | Xóa bộ lọc hoặc kiểm tra lại camera và khoảng ngày. |
| Ảnh không đúng kích thước | Chọn ảnh cùng chiều rộng và chiều cao với ảnh tham chiếu. |
| Xử lý ảnh thất bại | Kiểm tra AI service đã sẵn sàng và xem mã lỗi hiển thị. |
| Không có quyền cấu hình | Đăng nhập bằng tài khoản Admin được cấp. |

Không gửi mật khẩu hoặc token khi chia sẻ thông tin lỗi.
