import { useEffect, useState } from "react";
import { fetchCameras } from "../api/parking";
import { getSnapshot, getSnapshotImage, listSnapshots } from "../api/snapshots";
import SpotLabels from "./SpotLabels";
import PredictionReview from "./PredictionReview";
import { filterSnapshotsByOccupancy } from "../api/snapshotFiltering";
import { snapshotCsv } from "../api/snapshotCsv";

const PAGE_SIZE = 20;
const jobNames = { queued: "Đang chờ", processing: "Đang xử lý", completed: "Hoàn thành", failed: "Thất bại" };
const labels = { empty: "Trống", occupied: "Có xe", unknown: "Chưa xác định" };
const colors = { empty: "#16a34a", occupied: "#dc2626", unknown: "#64748b" };
const emptyFilters = { camera: "", status: "", occupancy: "", from: "", to: "" };

function message(error) {
  if (error.message === "OCCUPANCY_FILTER_TOO_MANY") return "Có hơn 500 snapshot hoàn thành. Hãy thu hẹp khoảng ngày hoặc chọn camera trước khi lọc trạng thái ô.";
  if (error.message === "OCCUPANCY_FILTER_CHANGED") return "Dữ liệu đã thay đổi trong lúc lọc. Hãy thử áp dụng lại bộ lọc.";
  if (error.response?.status === 401) return "Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.";
  if (error.response?.status === 403) return "Bạn không có quyền xem dữ liệu này.";
  if (error.response?.status === 404) return "Snapshot không còn tồn tại hoặc ảnh không khả dụng.";
  return "Không tải được dữ liệu. Hãy kiểm tra kết nối backend và thử lại.";
}

function downloadCsv(snapshot, cameraName) {
  const blob = new Blob([snapshotCsv(snapshot, cameraName)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `snapshot-${snapshot.id}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function SnapshotDetail({ id, cameraNames, report }) {
  const [state, setState] = useState({ status: "loading", data: null, error: "" });
  const [image, setImage] = useState({ url: "", error: "" });
  const [reviewId, setReviewId] = useState("");
  useEffect(() => {
    let active = true;
    getSnapshot(id).then((data) => {
      if (active) setState({ status: "ready", data, error: "" });
    }).catch((error) => {
      if (active) setState({ status: "error", data: null, error: message(error) });
    });
    return () => { active = false; };
  }, [id]);

  useEffect(() => {
    let active = true;
    let url;
    getSnapshotImage(id).then((blob) => {
      if (!active) return;
      url = URL.createObjectURL(blob);
      setImage({ url, error: "" });
    }).catch((error) => { if (active) setImage({ url: "", error: message(error) }); });
    return () => { active = false; if (url) URL.revokeObjectURL(url); };
  }, [id]);

  if (state.status === "loading") return <p role="status">Đang tải chi tiết snapshot...</p>;
  if (state.status === "error") return <p className="manager-error" role="alert">{state.error}</p>;
  const snapshot = state.data;
  const summary = snapshot.summary;
  return <div className="snapshot-detail">
    <h3>Chi tiết snapshot</h3>
    <p>Camera: {cameraNames[snapshot.camera_id] || snapshot.camera_id} · Chụp lúc: {new Date(snapshot.captured_at).toLocaleString("vi-VN")}</p>
    <p>Trạng thái xử lý: {jobNames[snapshot.job_status] || snapshot.job_status}{snapshot.error_code ? ` · Mã lỗi: ${snapshot.error_code}` : ""}</p>
    {summary && <p>Tổng: {summary.total} · Trống: {summary.empty} · Có xe: {summary.occupied} · Chưa xác định: {summary.unknown} · Tỷ lệ sử dụng: {summary.occupancy_rate == null ? "—" : `${summary.occupancy_rate}%`}</p>}
    {snapshot.job_status === "completed" && <p>{snapshot.is_stale == null ? "Chưa xác định độ mới của dữ liệu." : snapshot.is_stale ? "Dữ liệu đã cũ (STALE)." : "Dữ liệu trong ngưỡng thời gian."} Model: {snapshot.ai_model_version || "Không có thông tin"}</p>}
    {image.error && <p role="alert">{image.error}</p>}
    {image.url && <div className="dashboard-image">
      <img src={image.url} alt="Ảnh snapshot được chọn" />
      <svg viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden="true">
        {snapshot.predictions.map((spot) => <polygon key={spot.id} points={spot.polygon.map((p) => `${p.x},${p.y}`).join(" ")} fill={colors[spot.effective_label] || colors.unknown} fillOpacity="0.4" stroke={colors[spot.effective_label] || colors.unknown} strokeWidth="0.004" />)}
      </svg>
      <SpotLabels spots={snapshot.predictions} />
    </div>}
    {summary && <>
      <p>Nhãn hiện tại bao gồm kết quả xác minh mới nhất; dự đoán AI ban đầu được giữ nguyên.</p>
      <div className="manager-table-wrap"><table className="manager-table">
        <thead><tr><th>Mã ô</th><th>Dự đoán AI</th><th>Nhãn hiện tại</th><th>Confidence</th>{!report && <th>Xác minh</th>}</tr></thead>
        <tbody>{snapshot.predictions.map((spot) => <tr key={spot.id}><td>{spot.spot_code}</td><td>{labels[spot.predicted_label] || spot.predicted_label}</td><td>{labels[spot.effective_label] || spot.effective_label}</td><td>{typeof spot.confidence === "number" ? `${(spot.confidence * 100).toFixed(1)}%` : "—"}</td>{!report && <td><button type="button" aria-pressed={reviewId === spot.id} onClick={() => setReviewId(spot.id)}>Xác minh</button></td>}</tr>)}</tbody>
      </table></div>
      {!report && reviewId && <PredictionReview key={reviewId} spot={snapshot.predictions.find((spot) => spot.id === reviewId)} onRefresh={async () => {
        const data = await getSnapshot(id);
        setState({ status: "ready", data, error: "" });
      }} />}
      {report && <button type="button" className="manager-primary snapshot-export" onClick={() => downloadCsv(snapshot, cameraNames[snapshot.camera_id] || snapshot.camera_id)}>Tải CSV snapshot này</button>}
    </>}
  </div>;
}

export default function SnapshotHistory({ report = false }) {
  const [cameras, setCameras] = useState([]);
  const [cameraError, setCameraError] = useState("");
  const [draft, setDraft] = useState(emptyFilters);
  const [query, setQuery] = useState({ ...emptyFilters, offset: 0 });
  const [page, setPage] = useState({ status: "loading", items: [], total: 0, error: "" });
  const [selected, setSelected] = useState("");
  const [formError, setFormError] = useState("");

  useEffect(() => {
    let active = true;
    fetchCameras().then((items) => { if (active) setCameras(items); })
      .catch((error) => { if (active) setCameraError(message(error)); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    const params = {
      limit: PAGE_SIZE, offset: query.offset,
      ...(query.camera && { camera_id: query.camera }),
      ...(query.status && { job_status: query.status }),
      ...(query.from && { from: new Date(`${query.from}T00:00:00`).toISOString() }),
      ...(query.to && { to: new Date(`${query.to}T23:59:59.999`).toISOString() }),
    };
    const request = query.occupancy
      ? filterSnapshotsByOccupancy(params, query.occupancy, listSnapshots, getSnapshot)
        .then((items) => ({ items: items.slice(query.offset, query.offset + PAGE_SIZE), total: items.length }))
      : listSnapshots(params);
    request.then((data) => {
      if (active) setPage({ status: "ready", items: data.items, total: data.total, error: "" });
    }).catch((error) => {
      if (active) setPage({ status: "error", items: [], total: 0, error: message(error) });
    });
    return () => { active = false; };
  }, [query]);

  function applyFilters(event) {
    event.preventDefault();
    if (draft.from && draft.to && draft.from > draft.to) {
      setFormError("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.");
      return;
    }
    setFormError("");
    setSelected("");
    setPage({ status: "loading", items: [], total: 0, error: "" });
    setQuery({ ...draft, offset: 0 });
  }

  function move(offset) {
    setSelected("");
    setPage({ status: "loading", items: [], total: 0, error: "" });
    setQuery((old) => ({ ...old, offset }));
  }

  const cameraNames = Object.fromEntries(cameras.map((camera) => [camera.id, camera.name]));
  return <div className="dashboard-page">
    <form className="content-card" onSubmit={applyFilters}>
      <h2>{report ? "Báo cáo theo snapshot" : "Lịch sử snapshot"}</h2>
      <p>Lọc theo camera, thời gian chụp, trạng thái xử lý và nhãn hiện tại của ô.</p>
      {cameraError && <p className="manager-error" role="alert">Không tải được danh sách camera: {cameraError}</p>}
      <div className="snapshot-filters">
        <label>Camera<select value={draft.camera} onChange={(e) => setDraft({ ...draft, camera: e.target.value })}><option value="">Tất cả camera</option>{cameras.map((camera) => <option key={camera.id} value={camera.id}>{camera.name}</option>)}</select></label>
        <label>Trạng thái xử lý<select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}><option value="">Tất cả trạng thái</option>{Object.entries(jobNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label>Trạng thái ô<select value={draft.occupancy} onChange={(e) => setDraft({ ...draft, occupancy: e.target.value })}><option value="">Tất cả trạng thái ô</option>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>Có ô {label.toLowerCase()}</option>)}</select></label>
        <label>Từ ngày<input type="date" value={draft.from} onChange={(e) => setDraft({ ...draft, from: e.target.value })} /></label>
        <label>Đến ngày<input type="date" value={draft.to} onChange={(e) => setDraft({ ...draft, to: e.target.value })} /></label>
        <button className="manager-primary">Áp dụng bộ lọc</button>
      </div>
      {draft.occupancy && <p className="manager-hint">Lọc snapshot hoàn thành có ít nhất một ô mang nhãn hiện tại đã chọn. Sau khi xác minh, áp dụng lại bộ lọc để cập nhật danh sách.</p>}
      {formError && <p className="manager-error" role="alert">{formError}</p>}
    </form>
    <section className="content-card">
      {page.status === "loading" && <p role="status">Đang tải lịch sử...</p>}
      {page.status === "error" && <p className="manager-error" role="alert">{page.error}</p>}
      {page.status === "ready" && !page.items.length && <p>Không có snapshot phù hợp với bộ lọc.</p>}
      {page.status === "ready" && page.items.length > 0 && <>
        <p>Tìm thấy {page.total} snapshot. Chọn một dòng để xem chi tiết{report ? " và tải CSV" : ""}.</p>
        <div className="manager-table-wrap"><table className="manager-table">
          <thead><tr><th>Thời gian chụp</th><th>Camera</th><th>Trạng thái xử lý</th><th>Chi tiết</th></tr></thead>
          <tbody>{page.items.map((item) => <tr key={item.id}><td>{new Date(item.captured_at).toLocaleString("vi-VN")}</td><td>{cameraNames[item.camera_id] || item.camera_id}</td><td>{jobNames[item.job_status] || item.job_status}</td><td><button type="button" onClick={() => setSelected(item.id)} aria-pressed={selected === item.id}>Xem chi tiết</button></td></tr>)}</tbody>
        </table></div>
        <div className="snapshot-pagination">
          <button type="button" disabled={query.offset === 0} onClick={() => move(Math.max(0, query.offset - PAGE_SIZE))}>Trang trước</button>
          <span>{query.offset + 1}–{query.offset + page.items.length} / {page.total}</span>
          <button type="button" disabled={query.offset + page.items.length >= page.total} onClick={() => move(query.offset + PAGE_SIZE)}>Trang sau</button>
        </div>
      </>}
      {selected && <SnapshotDetail key={selected} id={selected} cameraNames={cameraNames} report={report} />}
    </section>
  </div>;
}
