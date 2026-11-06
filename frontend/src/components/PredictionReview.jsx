import { useEffect, useState } from "react";
import { createPredictionReview, getPredictionReviews } from "../api/snapshots";

const labels = { empty: "Trống", occupied: "Có xe", unknown: "Chưa xác định" };

function explain(error) {
  const status = error.response?.status;
  if (status === 401) return "Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.";
  if (status === 403) return "Bạn không có quyền xác minh kết quả.";
  if (status === 404) return "Không tìm thấy kết quả dự đoán.";
  if (status === 409) return "Kết quả đã thay đổi hoặc snapshot chưa hoàn thành. Hãy tải lại lịch sử trước khi gửi.";
  if (status === 422) return "Dữ liệu chưa hợp lệ. Hãy kiểm tra nhãn và lý do.";
  return "Không thể kết nối hoặc lưu xác minh. Hãy tải lại lịch sử trước khi thử lại.";
}

export default function PredictionReview({ spot, onRefresh }) {
  const [reviews, setReviews] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [action, setAction] = useState("accept");
  const [label, setLabel] = useState("");
  const [reason, setReason] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    getPredictionReviews(spot.id).then((data) => {
      if (active) setReviews(data);
    }).catch((err) => { if (active) setError(explain(err)); });
    return () => { active = false; };
  }, [spot.id, reloadKey]);

  async function reload() {
    setReviews(null);
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await onRefresh();
      setReloadKey((value) => value + 1);
    } catch (err) {
      setError(explain(err));
    } finally {
      setBusy(false);
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (!reviews) return;
    if (action === "correct" && (!label || label === spot.predicted_label || !reason.trim())) {
      setError("Chọn nhãn khác dự đoán AI và nhập lý do chỉnh sửa.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    const revision = reviews.length ? reviews[reviews.length - 1].revision : 0;
    const payload = { action, expected_revision: revision };
    if (action === "correct") {
      payload.verified_label = label;
      payload.reason = reason.trim();
    }
    try {
      await createPredictionReview(spot.id, payload);
      setReviews(null);
      setLabel("");
      setReason("");
      setAction("accept");
      try {
        await onRefresh();
        setNotice("Đã lưu xác minh và cập nhật snapshot.");
        setReloadKey((value) => value + 1);
      } catch {
        setError("Đã lưu xác minh nhưng không tải lại được snapshot. Hãy tải lại trang.");
      }
    } catch (err) {
      // The request may have reached the server even if the response was lost.
      setReviews(null);
      setError(explain(err));
    } finally {
      setBusy(false);
    }
  }

  return <section className="review-panel" aria-label={`Xác minh ${spot.spot_code}`}>
    <h4>Xác minh ô {spot.spot_code}</h4>
    <p>Dự đoán AI: {labels[spot.predicted_label] || spot.predicted_label} · Nhãn hiện tại: {labels[spot.effective_label] || spot.effective_label}</p>
    {notice && <p className="manager-success" role="status">{notice}</p>}
    {error && <p className="manager-error" role="alert">{error}</p>}
    {!reviews && !error && <p role="status">Đang tải lịch sử xác minh...</p>}
    {!reviews && error && <button type="button" onClick={reload} disabled={busy}>Tải lại lịch sử</button>}
    {reviews && <>
      <p>{reviews.length ? `Lần xác minh gần nhất: phiên bản ${reviews[reviews.length - 1].revision}` : "Chưa có xác minh."}</p>
      {reviews.length > 0 && <details><summary>Lịch sử xác minh ({reviews.length})</summary>
        <ul>{reviews.map((review) => <li key={review.id}>{new Date(review.changed_at).toLocaleString("vi-VN")} · {review.action === "accept" ? "Xác nhận dự đoán" : "Chỉnh sửa"} · {labels[review.verified_label] || review.verified_label} · Người xác minh: {review.reviewer_id}{review.reason ? ` · Lý do: ${review.reason}` : ""}</li>)}</ul>
      </details>}
      <form onSubmit={submit} className="review-form">
        <label>Thao tác<select value={action} onChange={(event) => { setAction(event.target.value); setError(""); }}>
          <option value="accept">Xác nhận dự đoán AI</option>
          <option value="correct">Sửa nhãn dự đoán</option>
        </select></label>
        {action === "correct" && <>
          <label>Nhãn sau khi sửa<select value={label} onChange={(event) => setLabel(event.target.value)} required>
            <option value="">Chọn nhãn</option>
            {Object.entries(labels).filter(([value]) => value !== spot.predicted_label).map(([value, text]) => <option key={value} value={value}>{text}</option>)}
          </select></label>
          <label>Lý do<textarea value={reason} onChange={(event) => setReason(event.target.value)} maxLength={1000} required /></label>
        </>}
        <button className="manager-primary" disabled={busy}>{busy ? "Đang lưu..." : "Lưu xác minh"}</button>
      </form>
    </>}
  </section>;
}
