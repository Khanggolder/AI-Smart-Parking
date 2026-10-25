# Mục lục bằng chứng phần AI

Để hiểu hệ thống từ đầu, đọc [README](../README.md) → [System Overview](../docs/SYSTEM_OVERVIEW.md) → [Source Code Guide](../docs/SOURCE_CODE_GUIDE.md). Để luyện trình bày, đọc [Defense Guide](../docs/DEFENSE_GUIDE.md). Các báo cáo dưới đây lưu lại cách làm và giới hạn; không cần đọc theo tuần nếu chỉ muốn chạy demo.

## Kết quả nên mở khi cần chứng cứ

| Tài liệu | Có gì |
|---|---|
| [Báo cáo AI cuối](final_ai_report.md) | Tóm tắt dữ liệu, model, test, benchmark, giới hạn; tiêu đề lịch sử ghi rc1, release tích hợp hiện là rc2. |
| [W5 independent evaluation](w5_evaluation_report.md) | Protocol test 740 crop, confusion matrix, UNKNOWN, hai false empty và phân tích lỗi. |
| [W5 benchmark](w5_benchmark_report.md) | Đo engine/HTTP localhost, phân biệt 37 polygon thật với workload 50/100 lặp polygon. |
| [Model Card](../docs/MODEL_CARD.md) | Model, nguồn dữ liệu, hash, phạm vi dùng và những điều chưa kiểm. |
| [AI API Contract](../docs/AI_API_CONTRACT.md) | Request/response, mã lỗi và giới hạn endpoint đang chạy. |

## Lịch sử nghiên cứu và bàn giao

| Nhóm | Báo cáo hiện có | Mục đích |
|---|---|---|
| Dataset W0/W1 | [Inspection](dataset_inspection.md), [Preparation](dataset_preparation.md), [split stats](dataset_split_stats.json), [crop preview](crops_preview.jpg) | Nguồn UFPR04, kiểm annotation/overlay, chia theo ngày và tạo crop. |
| Model W2/W3 | [W3 confidence](w3_confidence_analysis.md), [Model Card](../docs/MODEL_CARD.md) | Nêu checkpoint W2, phân tích validation và ngưỡng ứng viên. W2 history/checkpoint chi tiết nằm trong `runs/` bị Git ignore; không có báo cáo W2 riêng trong `reports/`. |
| Inference W4 | [W4 inference report](w4_inference_report.md) | API, kiểm request/crop, smoke. |
| Evaluation W5 | [Evaluation](w5_evaluation_report.md), [benchmark](w5_benchmark_report.md), [limitations](w5_limitations.md) | Test độc lập, đo độ trễ, giới hạn. JSON/CSV/gallery chi tiết trong `runs/` local, không ở GitHub. |
| Release W6 | [W6 checklist](w6_release_checklist.md), [release readme](../docs/RELEASE_README.md), [backend handover](../docs/BACKEND_HANDOVER.md) | Đóng gói, xác minh, bàn giao rc1/rc2. ZIP nằm ngoài Git. |
| Cleanup W7 | [audit](w7_repository_audit.md), [changelog](w7_cleanup_changelog.md), [verification](w7_verification_report.md), [integration readiness](w7_integration_readiness.md) | Giải thích refactor nhỏ và đối chiếu regression. |
| Git W8 | [Git audit](w8_git_audit.md), [finalization](w8_git_finalization.md), [issue status](w8_issue_status.md), [PR description](w8_pr_description.md), [integration plan](../docs/BACKEND_AI_INTEGRATION_PLAN.md) | Những gì đã đưa lên branch/PR và việc backend còn phải làm. |

Các file ở đây là bằng chứng lịch sử, không phải tất cả đều mô tả đúng trạng thái release mới nhất. Ví dụ [báo cáo cuối](final_ai_report.md) ghi rc1 tại thời điểm viết; xem [Model Card rc2](../docs/MODEL_CARD.md) và [Release README](../docs/RELEASE_README.md) khi hỏi gói tích hợp hiện hành. Không chỉnh các số đo W5 theo demo sau này.
