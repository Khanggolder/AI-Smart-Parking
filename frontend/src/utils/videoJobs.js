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
