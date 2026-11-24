import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import VideoAutoAnalysis from "./VideoAutoAnalysis";
import VideoReferenceImage from "./VideoReferenceImage";

export default function VideoFramePreview({ production = false, role = "operator" }) {
  const videoRef = useRef(null);
  const generation = useRef(0);
  const [videoUrl, setVideoUrl] = useState("");
  const [frame, setFrame] = useState(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [monitoring, setMonitoring] = useState(false);
  const [referenceBusy, setReferenceBusy] = useState(false);

  useEffect(() => () => { if (videoUrl) URL.revokeObjectURL(videoUrl); }, [videoUrl]);
  useEffect(() => () => { if (frame?.url) URL.revokeObjectURL(frame.url); }, [frame]);
  useEffect(() => () => { generation.current += 1; }, []);

  function chooseVideo(event) {
    const file = event.target.files?.[0];
    generation.current += 1;
    setFrame(null);
    setReady(false);
    setBusy(false);
    setError("");
    if (!file) {
      setVideoUrl("");
      return;
    }
    if (!/\.mp4$/i.test(file.name)) {
      setVideoUrl("");
      setError("Hãy chọn một file MP4.");
      return;
    }
    setVideoUrl(URL.createObjectURL(file));
  }

  function capture() {
    const video = videoRef.current;
    if (!video || video.readyState < 2 || video.seeking || !video.videoWidth || !video.videoHeight) {
      setError("Frame chưa sẵn sàng. Hãy đợi video tải xong hoặc đợi tua xong.");
      return;
    }
    if (video.videoWidth * video.videoHeight > 20_000_000) {
      setError("Frame vượt giới hạn 20 triệu pixel của backend.");
      return;
    }
    setError("");
    video.pause();
    const width = video.videoWidth;
    const height = video.videoHeight;
    const seconds = video.currentTime;
    const version = generation.current;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) {
      setError("Trình duyệt không thể tạo canvas.");
      return;
    }
    setBusy(true);
    try {
      context.drawImage(video, 0, 0, width, height);
      canvas.toBlob((blob) => {
        if (generation.current !== version) return;
        setBusy(false);
        if (!blob || blob.type !== "image/jpeg") {
          setError("Không thể tạo ảnh JPEG từ frame này.");
          return;
        }
        setFrame({ url: URL.createObjectURL(blob), blob, seconds, width, height, size: blob.size });
      }, "image/jpeg", 0.92);
    } catch {
      setBusy(false);
      setError("Không thể đọc frame này. Hãy thử video khác.");
    }
  }

  return <div className={production ? "video-frame-preview" : "main-content video-frame-preview"}>
    <section className="content-card">
      <h1>Phân tích video MP4</h1>
      <p>Chọn video trên máy, phát hoặc tua đến vị trí cần kiểm tra rồi chọn <strong>Chụp frame</strong>. Video được đọc tại trình duyệt.</p>
      <label className="video-frame-file">Video MP4
        <input type="file" accept=".mp4,video/mp4" onChange={chooseVideo} disabled={monitoring || referenceBusy} />
      </label>
      {videoUrl && <video key={videoUrl} ref={videoRef} src={videoUrl} controls playsInline
        onLoadedData={(event) => {
          const video = event.currentTarget;
          const hasVideo = video.videoWidth > 0 && video.videoHeight > 0;
          setReady(hasVideo);
          setError(hasVideo ? "" : "Không tìm thấy hình ảnh video có thể phát. File có thể dùng codec không được trình duyệt hỗ trợ; hãy thử MP4 H.264.");
        }}
        onError={() => { setReady(false); setError("Trình duyệt không thể phát file này. Hãy thử MP4 với codec được trình duyệt hỗ trợ."); }} />}
      {videoUrl && <button className="manager-primary" type="button" onClick={capture} disabled={!ready || busy || monitoring || referenceBusy}>
        {busy ? "Đang tạo ảnh..." : "Chụp frame"}
      </button>}
      {error && <p className="manager-error" role="alert">{error}</p>}
      {frame && <section className="video-frame-result">
        <h2>Frame đã chọn</h2>
        <p>Vị trí trong video: {frame.seconds.toFixed(2)} giây · Kích thước: {frame.width} × {frame.height} px · Dung lượng: {(frame.size / 1024 / 1024).toFixed(2)} MB</p>
        <img src={frame.url} alt="Frame vừa trích từ video" />
        <p>Ảnh cần có cùng kích thước và góc camera với ảnh tham chiếu. Vị trí trong video không phải thời gian chụp thực tế.</p>
        <a className="manager-primary video-frame-download" href={frame.url} download="video-frame.jpg">Tải ảnh JPEG</a>
        {production && role === "admin" && <VideoReferenceImage frame={frame} disabled={monitoring} setReferenceBusy={setReferenceBusy} />}
        <p>Nếu muốn thử AI, tải ảnh này lên Dashboard bằng luồng snapshot hiện có và nhập đúng thời gian chụp. Việc gửi ảnh sẽ tạo snapshot trong lịch sử.</p>
      </section>}
      <VideoAutoAnalysis key={`analysis:${videoUrl}`} videoRef={videoRef} ready={ready && !referenceBusy} monitoring={monitoring} setMonitoring={setMonitoring} production={production} />
      <p><Link to="/">Về Dashboard</Link></p>
    </section>
  </div>;
}
