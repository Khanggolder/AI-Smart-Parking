import { useEffect, useRef, useState } from "react";
import StatCard from "../components/StatCard";
import { fetchCameras } from "../api/parking";
import { getSnapshot, getSnapshotImage, listCompletedSnapshots, submitSnapshot } from "../api/snapshots";

const labels = { empty: "Trống", occupied: "Có xe", unknown: "Chưa xác định" };
const colors = { empty: "#16a34a", occupied: "#dc2626", unknown: "#64748b" };
const statuses = { FULL: "Bãi đã đầy", AVAILABLE: "Còn ô trống", UNDETERMINED: "Chưa thể xác định bãi đã đầy", NO_SPOTS: "Chưa có ô đỗ" };

function errorMessage(error) {
  const code = error.response?.data?.error?.code;
  const messages = {
    CAMERA_NOT_CONFIGURED: "Camera chưa có ảnh tham chiếu.",
    NO_ACTIVE_SPOTS: "Camera chưa có ô đỗ đang hoạt động.",
    IMAGE_DIMENSIONS_MISMATCH: "Kích thước ảnh phải khớp ảnh tham chiếu của camera.",
    CAMERA_SPOT_LIMIT: "Camera vượt quá giới hạn 100 ô đỗ.",
  };
  if (messages[code]) return messages[code];
  if (error.response?.status === 401) return "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.";
  if (error.response?.status === 413) return "Ảnh quá lớn. Vui lòng chọn ảnh nhỏ hơn.";
  if (error.response?.status === 415 || error.response?.status === 422) return "Ảnh hoặc thời gian chụp không hợp lệ. Hãy kiểm tra lại.";
  return error.response ? "Backend không thể xử lý yêu cầu. Vui lòng thử lại." : "Không kết nối được Backend. Vui lòng kiểm tra kết nối.";
}

function localNow() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function SnapshotImage({ snapshot }) {
  const [image, setImage] = useState({ url: null, error: false });
  useEffect(() => {
    let active = true;
    let objectUrl;
    getSnapshotImage(snapshot.id).then((blob) => {
      if (!active) return;
      objectUrl = URL.createObjectURL(blob);
      setImage({ url: objectUrl, error: false });
    }).catch(() => {
      if (active) setImage({ url: null, error: true });
    });
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [snapshot.id]);
  if (image.error) return <p role="alert">Không tải được ảnh snapshot. Hãy kiểm tra kết nối hoặc quyền truy cập.</p>;
  if (!image.url) return <p>Đang tải ảnh snapshot...</p>;
  return (
    <div className="dashboard-image">
      <img src={image.url} alt="Ảnh snapshot từ camera" />
      <svg viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden="true">
        {snapshot.predictions.map((spot) => (
          <polygon key={spot.id}
            points={spot.polygon.map((point) => `${point.x},${point.y}`).join(" ")}
            fill={colors[spot.effective_label] || colors.unknown} fillOpacity="0.4"
            stroke={colors[spot.effective_label] || colors.unknown} strokeWidth="0.004" />
        ))}
      </svg>
    </div>
  );
}

function CameraDashboard({ cameraId }) {
  const [snapshot, setSnapshot] = useState(null);
  const [initial, setInitial] = useState("loading");
  const [error, setError] = useState("");
  const [file, setFile] = useState(null);
  const [capturedAt, setCapturedAt] = useState(localNow);
  const [submitting, setSubmitting] = useState(false);
  const [job, setJob] = useState(null);
  const completedNewJob = useRef(false);
  const snapshotId = snapshot?.id;

  useEffect(() => {
    let active = true;
    listCompletedSnapshots(cameraId)
      .then((items) => items.length ? getSnapshot(items[0].id) : null)
      .then((result) => { if (active && !completedNewJob.current) { setSnapshot(result); setInitial("ready"); } })
      .catch((err) => { if (active) { setError(errorMessage(err)); setInitial("error"); } });
    return () => { active = false; };
  }, [cameraId]);

  useEffect(() => {
    if (!job || !["queued", "processing"].includes(job.job_status)) return;
    let active = true;
    let timer;
    async function poll() {
      try {
        const result = await getSnapshot(job.id);
        if (!active) return;
        if (result.job_status === "completed") {
          completedNewJob.current = true;
          setSnapshot(result);
          setInitial("ready");
          setJob(result);
          setError("");
        } else if (result.job_status === "failed") {
          setJob(result);
          setError(`Xử lý ảnh thất bại (${result.error_code || "lỗi AI"}). Kết quả thành công trước đó vẫn được giữ lại.`);
        } else {
          timer = setTimeout(poll, 2000);
        }
      } catch (err) {
        if (active) {
          setError(`${errorMessage(err)} Đang thử lại trạng thái xử lý.`);
          timer = setTimeout(poll, 5000);
        }
      }
    }
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [job]);

  useEffect(() => {
    if (!snapshotId) return;
    let active = true;
    const timer = setInterval(() => {
      getSnapshot(snapshotId).then((result) => {
        if (active && result.job_status === "completed") setSnapshot(result);
      }).catch(() => { if (active) setError("Không cập nhật được trạng thái dữ liệu. Vui lòng kiểm tra kết nối."); });
    }, 30000);
    return () => { active = false; clearInterval(timer); };
  }, [snapshotId]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file || !capturedAt || Number.isNaN(new Date(capturedAt).getTime())) {
      setError("Hãy chọn ảnh và thời gian chụp hợp lệ.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const accepted = await submitSnapshot(cameraId, file, new Date(capturedAt).toISOString());
      setJob(accepted);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  const busy = submitting || (job && ["queued", "processing"].includes(job.job_status));
  const summary = snapshot?.summary;
  return (
    <div className="dashboard-page">
      <form className="content-card dashboard-upload" onSubmit={handleSubmit}>
        <h2>Phân tích ảnh snapshot</h2>
        <p>Chọn ảnh JPEG/PNG cùng kích thước với ảnh tham chiếu của camera.</p>
        <div className="dashboard-fields">
          <label>Ảnh snapshot<input type="file" accept="image/jpeg,image/png" onChange={(event) => setFile(event.target.files?.[0] || null)} required /></label>
          <label>Thời gian chụp<input type="datetime-local" value={capturedAt} onChange={(event) => setCapturedAt(event.target.value)} required /></label>
          <button className="manager-primary" disabled={busy || !file}>{submitting ? "Đang tải ảnh..." : "Tải ảnh và phân tích"}</button>
        </div>
        {busy && !submitting && <p role="status">Ảnh đang chờ hoặc đang được AI xử lý...</p>}
        {error && <p className="manager-error" role="alert">{error}</p>}
      </form>

      {initial === "loading" && <section className="content-card" role="status">Đang tải kết quả gần nhất...</section>}
      {initial === "error" && !snapshot && <section className="content-card">Không tải được kết quả. Hãy kiểm tra backend và tải lại trang.</section>}
      {initial === "ready" && !snapshot && <section className="content-card">Chưa có snapshot được xử lý thành công cho camera này.</section>}
      {snapshot && summary && <>
        <div className="stats-grid">
          <StatCard title="Tổng số ô" value={summary.total} color="#2563eb" />
          <StatCard title="Ô trống" value={summary.empty} color={colors.empty} />
          <StatCard title="Đã có xe" value={summary.occupied} color={colors.occupied} />
          <StatCard title="Chưa xác định" value={summary.unknown} color={colors.unknown} />
        </div>
        <section className="content-card">
          <h2>Kết quả snapshot gần nhất</h2>
          <p><strong>{statuses[summary.status] || summary.status}</strong> · Tỷ lệ sử dụng: {summary.occupancy_rate == null ? "Chưa xác định" : `${summary.occupancy_rate}%`}</p>
          <p>Thời gian chụp: {new Date(snapshot.captured_at).toLocaleString("vi-VN")} · Model: {snapshot.ai_model_version || "Không có thông tin"}</p>
          <p>{snapshot.is_stale == null ? "Chưa xác định được độ mới của dữ liệu." : snapshot.is_stale ? "Dữ liệu đã cũ (STALE)." : "Snapshot còn trong ngưỡng thời gian."} Đây là ảnh chụp, không phải video trực tiếp.</p>
          <SnapshotImage key={snapshot.id} snapshot={snapshot} />
          <h3>Trạng thái từng ô</h3>
          <p>Confidence là điểm tin cậy của mô hình, chưa được hiệu chuẩn.</p>
          <div className="manager-table-wrap">
            <table className="manager-table">
              <thead><tr><th>Mã ô</th><th>Trạng thái</th><th>Confidence</th></tr></thead>
              <tbody>{snapshot.predictions.map((spot) => <tr key={spot.id}><td>{spot.spot_code}</td><td><span className="dashboard-dot" style={{ backgroundColor: colors[spot.effective_label] || colors.unknown }} />{labels[spot.effective_label] || "Chưa xác định"}</td><td>{typeof spot.confidence === "number" ? `${(spot.confidence * 100).toFixed(1)}%` : "Không có"}</td></tr>)}</tbody>
            </table>
          </div>
        </section>
      </>}
    </div>
  );
}

export default function Dashboard() {
  const [cameras, setCameras] = useState([]);
  const [selected, setSelected] = useState("");
  const [state, setState] = useState("loading");
  useEffect(() => {
    let active = true;
    fetchCameras().then((items) => {
      if (!active) return;
      setCameras(items);
      setSelected(items[0]?.id || "");
      setState("ready");
    }).catch(() => { if (active) setState("error"); });
    return () => { active = false; };
  }, []);
  if (state === "loading") return <section className="content-card" role="status">Đang tải danh sách camera...</section>;
  if (state === "error") return <section className="content-card" role="alert">Không tải được camera. Hãy kiểm tra kết nối backend và tải lại trang.</section>;
  if (!cameras.length) return <section className="content-card">Chưa có camera. Hãy cấu hình camera trước khi phân tích ảnh.</section>;
  return <>
    <section className="content-card dashboard-camera">
      <label htmlFor="dashboard-camera">Camera</label>
      <select id="dashboard-camera" className="manager-select" value={selected} onChange={(event) => setSelected(event.target.value)}>
        {cameras.map((camera) => <option key={camera.id} value={camera.id}>{camera.name}</option>)}
      </select>
    </section>
    <CameraDashboard key={selected} cameraId={selected} />
  </>;
}
