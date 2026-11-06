// The current API exposes occupancy only on snapshot details.
export async function filterSnapshotsByOccupancy(params, label, fetchList, fetchDetail) {
  if (params.job_status && params.job_status !== "completed") return [];
  const candidates = [];
  let expectedTotal = null;
  const seen = new Set();
  do {
    const page = await fetchList({ ...params, job_status: "completed", limit: 100, offset: candidates.length });
    if (!Array.isArray(page.items) || !Number.isInteger(page.total)) throw new Error("INVALID_PAGE");
    if (expectedTotal === null) {
      expectedTotal = page.total;
      if (expectedTotal > 500) throw new Error("OCCUPANCY_FILTER_TOO_MANY");
    }
    if (page.total !== expectedTotal || (page.items.length === 0 && candidates.length < expectedTotal)) throw new Error("OCCUPANCY_FILTER_CHANGED");
    for (const item of page.items) {
      if (seen.has(item.id)) throw new Error("OCCUPANCY_FILTER_CHANGED");
      seen.add(item.id);
      candidates.push(item);
    }
  } while (candidates.length < expectedTotal);
  if (candidates.length !== expectedTotal) throw new Error("OCCUPANCY_FILTER_CHANGED");

  const matches = [];
  for (let i = 0; i < candidates.length; i += 10) {
    const batch = candidates.slice(i, i + 10);
    const details = await Promise.all(batch.map((item) => fetchDetail(item.id)));
    details.forEach((detail, index) => {
      if (detail.job_status !== "completed" || !Array.isArray(detail.predictions)) throw new Error("OCCUPANCY_FILTER_CHANGED");
      if (detail.predictions.some((spot) => spot.effective_label === label)) matches.push(batch[index]);
    });
  }
  return matches;
}
