# Quy ước cộng tác (dự kiến)

## Phân công
- **Nguyễn Duy Khang (AI/Data):** dataset, baseline, đánh giá mô hình, AI inference.
- **Nguyễn Hoài Nam (Backend/BA):** SRS, ERD, API, auth, CRUD, lưu kết quả.
- **Nguyễn Hoàng Minh Khôi (Frontend/DevOps):** UI, polygon editor, dashboard, Docker/CI.

## Git workflow
1. Tạo GitHub Issue cho mỗi gói việc trong WBS; gắn ID WBS vào tiêu đề.
2. Tạo nhánh từ `main`: `feature/...`, `fix/...`, `docs/...`.
3. Commit nhỏ, rõ nội dung (ví dụ `feat: add parking spot editor`).
4. Tạo Pull Request về `main`, liên kết issue, mô tả cách kiểm thử.
5. Một thành viên khác review trước merge khi có thể. Không push trực tiếp vào `main` trong giai đoạn phát triển thông thường.

## Definition of Done
- Đã kiểm thử trường hợp thành công và lỗi.
- API thay đổi phải cập nhật contract; dữ liệu thay đổi cần migration.
- Không commit token, mật khẩu, ảnh nhạy cảm, dataset/model dung lượng lớn.
- README/docs khớp với chức năng thực tế.
- Kết quả AI phải do inference, không dùng nhãn ground truth để giả lập.

**Lưu ý:** Chưa có quy tắc branch protection được bật tự động; nhóm nên thống nhất sau review.
