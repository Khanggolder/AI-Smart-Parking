# Bàn giao dashboard cho Khôi

Hiển thị `label` cuối từ backend: `empty` màu xanh, `occupied` màu đỏ, `unknown` màu xám. Không tự suy nhãn từ `scores` hoặc `raw_label`, nhất là khi threshold khiến final label UNKNOWN. Hiển thị confidence cùng chú thích đó là max-softmax chưa hiệu chuẩn, `model_version` và thời gian snapshot do backend cung cấp. Khi service lỗi, hiển thị trạng thái unavailable/stale do backend xác định, không tô ô thành empty. Bản demo dùng camera cố định và polygon tương ứng; cần kiểm overlay polygon trên chính snapshot trình chiếu.
