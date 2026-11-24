import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCameras } from "../api/parking";
import { fetchCameraSpots } from "../api/spots";
import { uploadCameraReferenceImage } from "../api/referenceImages";
import { validateReferenceTarget } from "../utils/videoReference";

export default function VideoReferenceImage({ frame, disabled, setReferenceBusy }) {
  const navigate = useNavigate();
  const [cameras, setCameras] = useState([]);
  const [cameraId, setCameraId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchCameras().then((items) => {
      if (!active) return;
      setCameras(items);
      setCameraId("");
      setError("");
    }).catch(() => { if (active) setError("Không tải được camera. Hãy kiểm tra đăng nhập và Backend."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  async function useAsReference() {
    if (!cameraId || saving || disabled || !frame?.blob) return;
    const camera = cameras.find((item) => item.id === cameraId);
    setSaving(true);
    setReferenceBusy(true);
    setError("");
    try {
      const spots = await fetchCameraSpots(cameraId, true);
      const validation = validateReferenceTarget(camera, spots);
      if (validation) { setError(validation); return; }
      const question = camera.reference_image_path
        ? `Thay ảnh tham chiếu của ${camera.name} bằng frame tại ${frame.seconds.toFixed(2)} giây?`
        : `Dùng frame tại ${frame.seconds.toFixed(2)} giây làm ảnh tham chiếu cho ${camera.name}?`;
      if (!window.confirm(question)) return;
      const file = new File([frame.blob], "video-reference.jpg", { type: "image/jpeg" });
      await uploadCameraReferenceImage(cameraId, file, spots.camera_config_version);
      navigate(`/polygon-editor?cameraId=${encodeURIComponent(cameraId)}`);
    } catch (err) {
      const code = err.response?.data?.error?.code;
      setError(code === "ACTIVE_SPOTS_EXIST" ? "Camera đang có ô đỗ hoạt động. Hãy chọn camera khác hoặc ngừng kích hoạt các ô trước." : code === "CAMERA_VERSION_CONFLICT" ? "Cấu hình camera đã thay đổi. Hãy tải lại danh sách camera và thử lại." : err.response?.status === 403 ? "Chỉ Admin được thay ảnh tham chiếu." : !err.response ? "Không xác nhận được kết quả. Hãy kiểm tra ảnh camera trong Vẽ ô đỗ trước khi thử lại." : err.response?.data?.error?.message || "Không thể lưu ảnh tham chiếu.");
    } finally {
      setSaving(false);
      setReferenceBusy(false);
    }
  }

  return <div className="video-reference-image">
    <h3>Dùng frame làm ảnh tham chiếu</h3>
    <p>Chọn camera, rồi lưu frame đang xem để mở trang vẽ ô đỗ. Không thể thay ảnh nếu camera có ô đỗ đang hoạt động.</p>
    <div className="polygon-controls">
      <label>Camera<select className="manager-select" value={cameraId} disabled={loading || saving || disabled} onChange={(event) => setCameraId(event.target.value)}><option value="">-- Chọn camera --</option>{cameras.map((camera) => <option key={camera.id} value={camera.id}>{camera.name}</option>)}</select></label>
      <button type="button" className="manager-primary" disabled={!cameraId || loading || saving || disabled} onClick={useAsReference}>{saving ? "Đang lưu..." : "Dùng frame để vẽ ô đỗ"}</button>
      <button type="button" disabled={saving || disabled} onClick={() => { setLoading(true); setAttempt((value) => value + 1); }}>Tải lại camera</button>
    </div>
    {error && <p className="manager-error" role="alert">{error}</p>}
  </div>;
}
