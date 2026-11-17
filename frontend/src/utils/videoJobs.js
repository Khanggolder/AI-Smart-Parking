export function validateVideoCamera(camera, video) {
  if (!camera?.reference_width || !camera?.reference_height) return "Camera chưa có ảnh tham chiếu. Hãy cấu hình camera trước.";
  if (video.videoWidth !== camera.reference_width || video.videoHeight !== camera.reference_height) return `Video có kích thước ${video.videoWidth} × ${video.videoHeight}; ảnh tham chiếu là ${camera.reference_width} × ${camera.reference_height}.`;
  return "";
}

export function captureTime(base, position, production, now = Date.now()) {
  const captured = base + position * 1000;
  if (!Number.isFinite(captured)) throw new Error("Thời gian chụp không hợp lệ.");
  if (production && captured > now + 60_000) throw new Error("Thời gian chụp nằm trong tương lai. Hãy kiểm tra thời gian bắt đầu ghi video.");
  return new Date(captured).toISOString();
}

export async function waitBeforeNextFrame({ intervalMs, shouldStop, wait, now = Date.now }) {
  const nextAt = now() + intervalMs;
  while (!shouldStop() && now() < nextAt) await wait(Math.min(250, nextAt - now()));
  return !shouldStop();
}

export async function waitForVideoSnapshot(job, { getSnapshot, wait, now = Date.now, onWait = () => {}, timeout = 120_000 }) {
  const deadline = now() + timeout;
  while (["queued", "processing"].includes(job.job_status) && now() < deadline) {
    onWait();
    await wait(2000);
    try {
      job = await getSnapshot(job.id);
    } catch (cause) {
      throw Object.assign(new Error("Không kiểm tra được trạng thái snapshot.", { cause }), { uncertain: true });
    }
  }
  if (["queued", "processing"].includes(job.job_status)) {
    throw Object.assign(new Error("AI xử lý quá lâu; snapshot có thể vẫn đang chạy."), { uncertain: true });
  }
  if (job.job_status === "failed") throw new Error(`Phân tích thất bại (${job.error_code || "không rõ nguyên nhân"}).`);
  if (job.job_status !== "completed") throw Object.assign(new Error("Backend trả về trạng thái snapshot không hợp lệ."), { uncertain: true });
  return job;
}
