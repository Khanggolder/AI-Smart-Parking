import { useEffect, useRef, useState } from "react";
import { fetchCameras } from "../api/parking";
import { TOKEN_KEY } from "../api/auth";
import { getSnapshot, submitSnapshot } from "../api/snapshots";
import { waitForVideoSnapshot } from "../utils/videoJobs";
import { Link } from "react-router-dom";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function frameBlob(video) {
  return new Promise((resolve, reject) => {
    if (!video || video.readyState < 2 || video.seeking || !video.videoWidth || !video.videoHeight || video.videoWidth * video.videoHeight > 20_000_000) {
      reject(new Error("Frame chưa sẵn sàng hoặc vượt giới hạn kích thước."));
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) { reject(new Error("Không tạo được canvas.")); return; }
    try {
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => blob?.type === "image/jpeg" ? resolve(blob) : reject(new Error("Không tạo được ảnh JPEG.")), "image/jpeg", 0.92);
    } catch { reject(new Error("Không đọc được frame.")); }
  });
}

export default function VideoAutoAnalysis({ videoRef, ready, monitoring, setMonitoring }) {
  const [cameras, setCameras] = useState([]);
  const [cameraId, setCameraId] = useState("");
  const [startAt, setStartAt] = useState("");
  const [interval, setIntervalSeconds] = useState(5);
  const [limit, setLimit] = useState(3);
  const [acknowledged, setAcknowledged] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [locked, setLocked] = useState(false);
  const [cameraAttempt, setCameraAttempt] = useState(0);
  const stop = useRef(false);
  const active = useRef(false);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    let current = true;
    Promise.resolve().then(() => {
      if (!sessionStorage.getItem(TOKEN_KEY)) throw new Error("not_signed_in");
      return fetchCameras();
    }).then((items) => {
      if (current) { setCameras(items); setCameraId(items[0]?.id || ""); setError(""); }
    }).catch((err) => {
      if (!current) return;
      const statusCode = err.response?.status;
      setError(err.message === "not_signed_in" ? "Bạn chưa đăng nhập trong tab này. Hãy về Dashboard và đăng nhập trước." : statusCode === 401 ? "Phiên đăng nhập hết hạn. Hãy về Dashboard và đăng nhập lại trong tab này." : statusCode === 403 ? "Tài khoản không có quyền xem camera." : err.response ? "Backend không tải được danh sách camera. Hãy kiểm tra Backend và database." : "Không kết nối được Backend. Hãy kiểm tra cổng 8000 và cấu hình kết nối.");
    });
    return () => { current = false; mounted.current = false; stop.current = true; };
  }, [cameraAttempt]);

  async function start() {
    if (active.current || locked || !ready || !cameraId || !acknowledged) return;
    const base = new Date(startAt).getTime();
    if (!startAt || !Number.isFinite(base)) { setError("Hãy nhập thời gian bắt đầu video hợp lệ."); return; }
    if (!videoRef.current || videoRef.current.paused || videoRef.current.ended) { setError("Hãy phát video trước khi bắt đầu phân tích."); return; }
    const secondsBetween = Number(interval);
    const maxFrames = Number(limit);
    if (!Number.isInteger(secondsBetween) || secondsBetween < 5 || secondsBetween > 300 || !Number.isInteger(maxFrames) || maxFrames < 1 || maxFrames > 10) {
      setError("Chu kỳ phải từ 5–300 giây và số frame từ 1–10."); return;
    }
    active.current = true;
    stop.current = false;
    setMonitoring(true);
    setError("");
    let completed = 0;
    let lastPosition = -1;
    let uncertain = false;
    try {
      while (!stop.current && completed < maxFrames) {
        const video = videoRef.current;
        if (!video || video.paused || video.ended) { setStatus(`Đã dừng vì video tạm dừng hoặc kết thúc. Hoàn thành ${completed}/${maxFrames} frame.`); break; }
        if (video.seeking || video.currentTime <= lastPosition) throw new Error("Video đang tua hoặc chưa tiến tới frame mới. Hãy phát video rồi thử lại.");
        const position = video.currentTime;
        const blob = await frameBlob(video);
        if (stop.current) break;
        const capturedAt = new Date(base + position * 1000).toISOString();
        setStatus(`Đang gửi frame tại ${position.toFixed(2)} giây (${completed + 1}/${maxFrames})...`);
        let job;
        try { job = await submitSnapshot(cameraId, new File([blob], "video-frame.jpg", { type: "image/jpeg" }), capturedAt); }
        catch (err) {
          if (!err.response) uncertain = true;
          throw new Error(err.response?.data?.error?.message || (uncertain ? "Không xác nhận được ảnh đã được Backend nhận hay chưa." : "Backend từ chối ảnh; kiểm tra camera, ô đỗ và kích thước ảnh."), { cause: err });
        }
        if (!job?.id) { uncertain = true; throw new Error("Backend không trả mã snapshot hợp lệ."); }
        job = await waitForVideoSnapshot(job, {
          getSnapshot,
          wait: sleep,
          onWait: () => { if (mounted.current) setStatus(`${stop.current ? "Đang dừng; chờ" : "Đang chờ"} AI xử lý frame tại ${position.toFixed(2)} giây...`); },
        });
        completed += 1;
        lastPosition = position;
        if (mounted.current) setStatus(`Đã phân tích ${completed}/${maxFrames} frame. Xem kết quả trong Lịch sử hoặc Dashboard.`);
        if (!stop.current && completed < maxFrames) {
          const nextAt = Date.now() + secondsBetween * 1000;
          while (!stop.current && Date.now() < nextAt) await sleep(Math.min(250, nextAt - Date.now()));
        }
      }
      if (mounted.current && stop.current) setStatus(`Đã dừng. Hoàn thành ${completed}/${maxFrames} frame.`);
    } catch (err) {
      if (mounted.current) {
        const resultUncertain = uncertain || err.uncertain;
        setError(`${err.message}${resultUncertain ? " Hãy kiểm tra Lịch sử trước khi chạy lại; snapshot có thể đã được tạo." : ""}`);
        if (resultUncertain) setLocked(true);
      }
    } finally {
      active.current = false;
      if (mounted.current) setMonitoring(false);
    }
  }

  return <section className="video-auto-analysis">
    <h2>Thử phân tích video theo chu kỳ</h2>
    <p>Frame sẽ được gửi đến Backend và tạo snapshot thật trong Lịch sử. Chọn camera có ảnh tham chiếu cùng góc nhìn và kích thước video.</p>
    <div className="polygon-controls">
      <label>Camera<select className="manager-select" value={cameraId} disabled={monitoring} onChange={(event) => setCameraId(event.target.value)}><option value="">-- Chọn camera --</option>{cameras.map((camera) => <option key={camera.id} value={camera.id}>{camera.name}</option>)}</select></label>
      <label>Thời gian bắt đầu ghi video<input type="datetime-local" step="1" value={startAt} disabled={monitoring} onChange={(event) => setStartAt(event.target.value)} /></label>
      <label>Chu kỳ sau mỗi lần hoàn tất (giây)<input type="number" min="5" max="300" step="1" value={interval} disabled={monitoring} onChange={(event) => setIntervalSeconds(event.target.value)} /></label>
      <label>Số frame tối đa<input type="number" min="1" max="10" step="1" value={limit} disabled={monitoring} onChange={(event) => setLimit(event.target.value)} /></label>
    </div>
    <p><label><input type="checkbox" checked={acknowledged} disabled={monitoring} onChange={(event) => setAcknowledged(event.target.checked)} /> Tôi hiểu snapshot sẽ lưu vào lịch sử; nếu dùng thời gian giả lập thì dữ liệu lưu không được đánh dấu riêng.</label></p>
    <div className="polygon-controls">
      <button type="button" className="manager-primary" disabled={!ready || !cameraId || !acknowledged || monitoring || locked} onClick={start}>Bắt đầu phân tích</button>
      <button type="button" disabled={!monitoring} onClick={() => { stop.current = true; setStatus("Đang dừng; snapshot đã gửi vẫn sẽ được xử lý."); }}>Dừng</button>
    </div>
    {status && <p role="status">{status}</p>}
    {error && <p className="manager-error" role="alert">{error}</p>}
    {!cameras.length && <p><Link to="/">Về Dashboard để đăng nhập</Link>{" · "}<button type="button" disabled={monitoring} onClick={() => setCameraAttempt((value) => value + 1)}>Tải lại camera</button></p>}
    {locked && <p>Đã khóa chạy lại do trạng thái chưa rõ. Kiểm tra Lịch sử và chờ job hoàn tất trước khi tải lại trang.</p>}
  </section>;
}
