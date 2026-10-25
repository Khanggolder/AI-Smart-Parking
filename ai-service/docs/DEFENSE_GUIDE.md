# Tự luyện vấn đáp phần AI

Đọc [README](../README.md), [System Overview](SYSTEM_OVERVIEW.md) và [Source Code Guide](SOURCE_CODE_GUIDE.md) rồi tự trả lời trước khi xem gợi ý. Mỗi mục có câu trả lời ngắn để nói tự nhiên, phần đào sâu để mở source, và điều cần tránh. Số liệu là kết quả trên bộ UFPR04 đã báo cáo, không phải cam kết cho mọi camera. Có thể thừa nhận điều chưa đo.

## 1. Tổng quan (1–5)

**1. AI Smart Parking giải quyết bài toán gì?**<br>
**Ngắn:** Xác định từng ô đỗ trong ảnh camera cố định đang trống hay có xe. Polygon của từng ô đã được cấu hình trước.<br>
**Sâu/source:** [System Overview](SYSTEM_OVERVIEW.md), `src/inference.py:InferenceEngine.infer`. **Tránh:** nói AI tự phát hiện vị trí ô.

**2. Vai trò AI so với backend và frontend?**<br>
**Ngắn:** AI nhận ảnh và polygon, trả nhãn cùng điểm dự đoán. Backend lưu snapshot/kết quả và tính FULL/STALE; frontend cho chỉnh polygon và hiển thị.<br>
**Sâu/source:** `src/service.py`, [Integration Plan](BACKEND_AI_INTEGRATION_PLAN.md). **Tránh:** gán lưu DB hay FULL cho AI.

**3. Vì sao camera cố định phù hợp polygon?**<br>
**Ngắn:** Góc nhìn ổn định giúp cấu hình trước vùng của từng ô rồi cắt cùng vị trí trên các ảnh sau. Nếu camera lệch, polygon phải được kiểm tra và cập nhật.<br>
**Sâu/source:** `src/preprocessing.py:polygon_pixels`. **Tránh:** xem polygon là tự thích nghi.

**4. Vì sao không dùng YOLO cho toàn bãi?**<br>
**Ngắn:** MVP này đã có vị trí ô từ cấu hình nên chọn phân loại từng crop bằng MobileNetV3-Small. Repo hiện không triển khai YOLO; chưa có so sánh thực nghiệm YOLO để kết luận mô hình nào tốt hơn.<br>
**Sâu/source:** `src/model_runtime.py:create_model`, [Model Card](MODEL_CARD.md). **Tránh:** khẳng định YOLO kém hơn.

**5. Có dùng được nhiều camera ngay không?**<br>
**Ngắn:** API nhận `camera_id` và có thể nhận request khác nhau, nhưng mô hình mới được đánh giá chính thức trên UFPR04. Camera mới cần polygon và tập ảnh có nhãn để kiểm tra lại.<br>
**Sâu/source:** `src/service.py:infer`, [W5 Evaluation](../reports/w5_evaluation_report.md). **Tránh:** suy accuracy UFPR04 cho camera khác.

## 2. Dữ liệu (6–11)

**6. MetaPKLot/PKLot là gì?**<br>
**Ngắn:** Đây là nguồn ảnh bãi xe và annotation dùng trong phần nghiên cứu. Bài này chọn camera UFPR04 để chuẩn bị crop ô đỗ.<br>
**Sâu/source:** [dataset inspection](../reports/dataset_inspection.md), `scripts/prepare_dataset.py`. **Tránh:** nói dữ liệu do nhóm tự chụp.

**7. Vì sao chọn UFPR04?**<br>
**Ngắn:** UFPR04 có ảnh và polygon annotation để xây pipeline kiểm chứng từ crop đến API. Việc chọn một camera giới hạn phạm vi kết luận; cần kiểm camera khác sau.<br>
**Sâu/source:** [dataset preparation](../reports/dataset_preparation.md). **Tránh:** gọi UFPR04 là đại diện mọi môi trường.

**8. Nhãn empty/occupied đến từ đâu?**<br>
**Ngắn:** Script chuẩn bị đọc annotation của dữ liệu nguồn và ghi nhãn cho từng crop vào CSV manifest. API phục vụ không nhận nhãn thật trong request.<br>
**Sâu/source:** `scripts/prepare_dataset.py:collect_records`, `src/dataset.py:LABEL_TO_ID`. **Tránh:** nói model tự sinh ground truth.

**9. Vì sao chia theo ngày?**<br>
**Ngắn:** Crop từ cùng ngày/ảnh rất giống nhau. Chia ngày riêng cho train, validation, test giảm nguy cơ một bối cảnh lặp lại ở cả lúc học và lúc đánh giá.<br>
**Sâu/source:** `scripts/prepare_dataset.py:split_days`, `src/baseline_utils.py:assert_safe_splits`. **Tránh:** nói cách chia này loại bỏ mọi thiên lệch.

**10. Data leakage là gì ở đây?**<br>
**Ngắn:** Đó là khi thông tin từ tập kiểm tra lọt vào huấn luyện/chọn mô hình, khiến số đo lạc quan. Code kiểm ngày, ảnh nguồn và đường dẫn crop không giao nhau giữa ba tập.<br>
**Sâu/source:** `assert_safe_splits`. **Tránh:** dùng test để chỉnh threshold sau W5.

**11. Train, validation, test khác nhau thế nào?**<br>
**Ngắn:** Train cập nhật trọng số; validation chọn checkpoint và khảo sát threshold; test độc lập đo kết quả sau khi khóa lựa chọn. Có 2.900/720/740 crop tương ứng.<br>
**Sâu/source:** `scripts/train_baseline.py`, `scripts/analyze_confidence.py`, `scripts/evaluate_independent.py`. **Tránh:** gọi validation 100% là test 100%.

## 3. Tiền xử lý (12–17)

**12. Polygon dùng để làm gì?**<br>
**Ngắn:** Polygon chỉ đúng phần ảnh của một ô đỗ. AI tạo một crop cho mỗi polygon rồi ghép prediction với `spot_id` tương ứng.<br>
**Sâu/source:** `src/preprocessing.py:preprocess`, `src/inference.py:InferenceEngine.infer`. **Tránh:** coi ID annotation dữ liệu là spot ID ổn định của hệ thống.

**13. Vì sao mask bên ngoài polygon?**<br>
**Ngắn:** Bounding box có thể chứa đường, cây hoặc ô bên cạnh. Tô xám ngoài polygon giúp phần model nhìn thấy tập trung vào vùng đã chọn.<br>
**Sâu/source:** `src/w1_crop.py:make_crop` tô BGR 114. **Tránh:** nói mask loại bỏ mọi bóng/che khuất bên trong.

**14. Letterbox là gì?**<br>
**Ngắn:** Crop được resize giữ tỷ lệ rồi thêm viền để thành 224×224. Cách này hạn chế méo hình so với kéo giãn trực tiếp.<br>
**Sâu/source:** `src/w1_crop.py:make_crop`, `scale=min(size/w,size/h)`. **Tránh:** nói không có bất kỳ mất mát ảnh nào.

**15. Vì sao đầu vào 224×224?**<br>
**Ngắn:** Pipeline huấn luyện và checkpoint đã khóa kích thước này; runtime kiểm metadata và shape tensor. Dùng kích thước khác sẽ không còn đúng cấu hình đã đánh giá.<br>
**Sâu/source:** `src/dataset.py`, `src/model_loader.py:ModelLoader.predict`. **Tránh:** khẳng định 224 là tối ưu tuyệt đối.

**16. Vì sao đổi BGR sang RGB?**<br>
**Ngắn:** OpenCV giải mã ảnh theo BGR, còn PIL/torchvision transform và dữ liệu huấn luyện dùng RGB. Đổi thứ tự kênh giữ màu nhất quán với lúc train.<br>
**Sâu/source:** `src/preprocessing.py:decode_image,preprocess`. **Tránh:** bỏ qua bước đổi màu khi giải thích.

**17. Vì sao chuẩn hóa ImageNet?**<br>
**Ngắn:** Crop RGB được đổi thành tensor và chuẩn hóa theo mean/std ImageNet như lúc học từ pretrained weights. Runtime kiểm đúng các hằng số trong cấu hình W3.<br>
**Sâu/source:** `src/preprocessing.py:TRANSFORM`, `src/model_loader.py:MEAN,STD`. **Tránh:** nói chuẩn hóa tự chứng minh model chính xác.

## 4. Model (18–23)

**18. MobileNetV3-Small là gì?**<br>
**Ngắn:** Đây là kiến trúc CNN phân loại ảnh của torchvision. Project thay lớp cuối để cho hai đầu ra empty/occupied.<br>
**Sâu/source:** `src/model_runtime.py:create_model`. **Tránh:** gọi nó là detector vẽ bounding box.

**19. Vì sao dùng pretrained?**<br>
**Ngắn:** Trọng số khởi tạo đã học đặc trưng ảnh tổng quát, giúp bắt đầu từ nền tốt hơn khi tập crop của project có hạn. Kết quả chính thức dùng checkpoint được fine-tune từ pretrained.<br>
**Sâu/source:** `train_baseline.py --weights pretrained`, checkpoint metadata trong [Model Card](MODEL_CARD.md). **Tránh:** coi smoke `--weights none` là baseline chính thức.

**20. Transfer learning diễn ra ra sao?**<br>
**Ngắn:** Training thay classifier cuối, ban đầu khóa backbone rồi mặc định mở từ epoch 3. Checkpoint tốt nhất được chọn theo validation macro-F1 và trong run báo cáo là epoch 2.<br>
**Sâu/source:** `scripts/train_baseline.py:main`. **Tránh:** nói checkpoint epoch 2 chứng minh bước mở backbone đã tạo cải thiện.

**21. Vì sao chọn MobileNetV3-Small?**<br>
**Ngắn:** Bài toán cần phân loại nhiều crop trong một ảnh nên kiến trúc gọn là lựa chọn thực dụng để thử latency. W5 đo trên máy demo; chưa có so sánh kiến trúc khác để chứng minh nó tối ưu.<br>
**Sâu/source:** [W5 Benchmark](../reports/w5_benchmark_report.md). **Tránh:** tuyên bố nhanh nhất.

**22. Model phân loại hai trạng thái thế nào?**<br>
**Ngắn:** Model nhận tensor của từng crop và xuất hai logits. Softmax cho hai điểm; lớp có điểm lớn hơn là `raw_label`.<br>
**Sâu/source:** `src/model_loader.py:predict`, `src/confidence_utils.py:decide`. **Tránh:** gọi UNKNOWN là logit thứ ba.

**23. Softmax có vai trò gì?**<br>
**Ngắn:** Softmax đổi hai logits thành hai điểm trong khoảng 0–1 và tổng gần 1. Điểm lớn nhất được dùng làm confidence để áp ngưỡng UNKNOWN.<br>
**Sâu/source:** `torch.softmax(logits, dim=1)` trong `ModelLoader.predict`. **Tránh:** diễn giải confidence là xác suất đúng đã hiệu chuẩn.

## 5. Huấn luyện và đánh giá (24–30)

**24. Loss function là gì?**<br>
**Ngắn:** Training dùng `CrossEntropyLoss` cho hai nhãn. Nó so logits với nhãn thật để cập nhật trọng số qua backpropagation.<br>
**Sâu/source:** `scripts/train_baseline.py:criterion`. **Tránh:** nói loss này trực tiếp tối ưu F1.

**25. Optimizer và learning rate?**<br>
**Ngắn:** Code dùng AdamW với learning rate mặc định 0,001 cho classifier và 0,00002 cho backbone, weight decay 1e-4. Đây là tham số run/CLI, không phải một định luật cho mọi camera.<br>
**Sâu/source:** `scripts/train_baseline.py:optimizer`. **Tránh:** khẳng định đã tìm tối ưu toàn diện.

**26. Early stopping là gì?**<br>
**Ngắn:** Nếu validation macro-F1 không cải thiện qua số epoch bằng `patience` (mặc định 4), vòng học dừng. Checkpoint tốt nhất vẫn được lưu từ lần validation cao nhất.<br>
**Sâu/source:** `scripts/train_baseline.py:stale`. **Tránh:** nói nó dùng test để dừng.

**27. Vì sao checkpoint ở epoch 2?**<br>
**Ngắn:** Run báo cáo chọn epoch 2 vì đó là lần validation macro-F1 tốt nhất theo quy tắc lưu checkpoint. Code không hard-code epoch này; cần xem history/checkpoint của run để kiểm thứ tự và tie.<br>
**Sâu/source:** [final report](../reports/final_ai_report.md), `train_baseline.py` điều kiện `val_macro_f1 > best_f1 + 1e-6`. **Tránh:** suy ra epoch sau chắc chắn overfit chỉ từ số epoch chọn.

**28. Accuracy, precision, recall, F1 khác nhau?**<br>
**Ngắn:** Accuracy đếm tỷ lệ dự đoán đúng tổng thể; precision xét trong những ô được dự đoán có xe có bao nhiêu đúng; recall xét trong ô thật có xe phát hiện được bao nhiêu. F1 là trung bình điều hòa precision và recall.<br>
**Sâu/source:** `src/baseline_utils.py:metrics_from_predictions`. **Tránh:** dùng accuracy một mình che false empty.

**29. Vì sao validation 100% nhưng test 97,973%?**<br>
**Ngắn:** Hai tập khác ngày và có phân bố/độ khó khác; validation còn được dùng chọn checkpoint. W5 test 740 crop cho kết quả thấp hơn, nên phải báo riêng. Chưa có thí nghiệm xác nhận một nguyên nhân đơn lẻ.<br>
**Sâu/source:** [W5 Evaluation](../reports/w5_evaluation_report.md). **Tránh:** gọi test là 100%.

**30. Ma trận nhầm lẫn cho thấy gì?**<br>
**Ngắn:** Hàng là nhãn thật, cột là dự đoán. Raw test `[[456,8],[7,269]]` có 7 occupied bị gọi empty và 8 empty bị gọi occupied; sau UNKNOWN còn 2 false empty được chấp nhận.<br>
**Sâu/source:** [W5 Evaluation](../reports/w5_evaluation_report.md). **Tránh:** đổi thứ tự hàng/cột.

## 6. UNKNOWN và độ tin cậy (31–35)

**31. UNKNOWN là gì?**<br>
**Ngắn:** Đây là nhãn cuối khi model không vượt ngưỡng điểm softmax. API vẫn giữ raw label và cả hai scores để có thể kiểm lại.<br>
**Sâu/source:** `src/confidence_utils.py:decide`, `src/inference.py`. **Tránh:** xem UNKNOWN là lỗi HTTP.

**32. Vì sao ngưỡng 0,90?**<br>
**Ngắn:** W3 khảo sát confidence trên validation và chọn 0,90 làm **ứng viên** rồi đóng băng trước W5 test. Nó chưa được xác nhận cho production hoặc camera khác.<br>
**Sâu/source:** [W3 report](../reports/w3_confidence_analysis.md), [Model Card](MODEL_CARD.md). **Tránh:** nói test được dùng chọn ngưỡng.

**33. UNKNOWN có được train như lớp thứ ba?**<br>
**Ngắn:** Không. Classifier có đúng hai đầu ra empty/occupied; UNKNOWN là quyết định sau softmax khi `max score < 0,90`.<br>
**Sâu/source:** `src/model_runtime.py:CLASSES,create_model`; `src/confidence_utils.py:decide`. **Tránh:** mô tả ba nhãn training.

**34. Hai false empty được chấp nhận có rủi ro gì?**<br>
**Ngắn:** Ô có xe nhưng AI nói trống có thể khiến người dùng bị dẫn tới ô không còn chỗ. Backend và UI phải phân biệt nhãn, ghi lịch sử và có quy trình kiểm tra; UNKNOWN không loại hết lỗi này.<br>
**Sâu/source:** [W5 Evaluation](../reports/w5_evaluation_report.md): confidence 0,9253 và 0,9497. **Tránh:** nói threshold bảo đảm an toàn.

**35. Confidence 0,95 có nghĩa đúng 95% không?**<br>
**Ngắn:** Không. Đó là điểm softmax của lần dự đoán; muốn diễn giải thành xác suất đúng cần đánh giá hiệu chuẩn trên dữ liệu phù hợp. Project chưa chứng minh hiệu chuẩn cho mọi bối cảnh.<br>
**Sâu/source:** `src/confidence_utils.py:decide`, [W3 report](../reports/w3_confidence_analysis.md). **Tránh:** nhân điểm với 100 để cam kết độ đúng.

## 7. API và tích hợp (36–40)

**36. FastAPI được dùng để làm gì?**<br>
**Ngắn:** Nó nhận multipart request và trả JSON/HTTP error. Model được nạp lúc ứng dụng khởi động, rồi dùng lại cho các request.<br>
**Sâu/source:** `src/service.py:create_app,lifespan,infer`. **Tránh:** nói mỗi request tải lại checkpoint.

**37. `/health` và `/ready` khác nhau?**<br>
**Ngắn:** `/health` báo tiến trình còn sống; `/ready` chỉ thành công khi model đã nạp. Thiếu checkpoint vẫn có thể health 200 nhưng ready 503.<br>
**Sâu/source:** `src/service.py:health,ready`. **Tránh:** dùng health 200 làm bằng chứng inference hoạt động.

**38. Backend gửi polygon thế nào?**<br>
**Ngắn:** AI nhận `spots_json` trong multipart cùng ảnh và `camera_id`; mỗi spot có ID và dãy cặp tọa độ `[x,y]` chuẩn hóa. Backend design v1 hiện dùng object `{x,y}` và đường dẫn khác, nên cần adapter theo kế hoạch W8.<br>
**Sâu/source:** [AI API Contract](AI_API_CONTRACT.md), [Integration Plan](BACKEND_AI_INTEGRATION_PLAN.md). **Tránh:** nói adapter đã triển khai.

**39. UNKNOWN, FULL, STALE thuộc ai?**<br>
**Ngắn:** AI trả UNKNOWN khi điểm thấp. Backend lưu nhãn này, xác định FULL từ tập spot hợp lệ và STALE từ thời điểm/kết nối; frontend thể hiện rõ từng trạng thái.<br>
**Sâu/source:** [Integration Plan](BACKEND_AI_INTEGRATION_PLAN.md). **Tránh:** tuyên bố tỷ lệ báo FULL sai đã được đo.

**40. AI service lỗi hoặc mất kết nối thì sao?**<br>
**Ngắn:** Backend cần đánh dấu job lỗi, giữ kết quả hoàn tất trước đó và thể hiện dữ liệu cũ/stale; không tự tạo prediction giả. Đây là hành vi tích hợp **đề xuất, chưa có runtime backend trong repo tại W9**.<br>
**Sâu/source:** [Integration Plan](BACKEND_AI_INTEGRATION_PLAN.md), `src/service.py` có lỗi 503/500. **Tránh:** trình bày kịch bản D trong demo như đã kiểm E2E.

## Kịch bản trình bày 3–5 phút

**Phút 1 — Bài toán.** “Em làm phần AI phân loại từng ô đỗ trên ảnh từ camera cố định. Ô đã được quản trị viên vẽ polygon. AI trả empty, occupied hoặc unknown; backend mới lưu lịch sử và quyết định FULL.”

**Phút 2 — Phương pháp.** Mở sơ đồ [System Overview](SYSTEM_OVERVIEW.md). Chỉ vào `service.py` nhận request, `preprocessing.py` kiểm polygon, `w1_crop.py` mask/letterbox, rồi `model_loader.py` chạy MobileNetV3-Small hai lớp. Giải thích UNKNOWN là ngưỡng trên softmax, không phải lớp học thêm.

**Phút 3 — Dữ liệu và kết quả.** Nêu train/val/test 2.900/720/740 crop chia theo ngày UFPR04; checkpoint epoch 2; test raw accuracy 97,973%, occupied F1 97,288%, 28 UNKNOWN và 2 false empty vẫn qua ngưỡng. Mở [W5 report](../reports/w5_evaluation_report.md) để chỉ ma trận.

**Phút 4 — Demo.** Với checkpoint rc2 đã xác minh, mở `/health`, `/ready`, gọi `/v1/infer` bằng ảnh và polygon đúng camera qua [runbook](DEMO_RUNBOOK.md). Chỉ `spot_id`, `raw_label`, final `label`, `confidence` trong JSON; nếu dashboard đã tích hợp thì xem dữ liệu từ backend. Không hard-code nhãn demo.

**Phút 5 — Giới hạn.** Nói rõ 37 polygon là benchmark localhost; chưa kiểm mưa/đêm/camera khác/FULL trên toàn bãi. Đề xuất thu ảnh có nhãn từ camera đích, kiểm polygon và đánh giá lại trước khi vận hành thật. Nếu thiếu artifact tại buổi demo, trình bày source và báo cáo đã kiểm thay vì dựng kết quả giả.
