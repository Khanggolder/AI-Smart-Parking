import test from "node:test";
import assert from "node:assert/strict";
import { filterSnapshotsByOccupancy } from "../src/api/snapshotFiltering.js";
import { snapshotCsv } from "../src/api/snapshotCsv.js";

test("occupancy filtering checks effective labels across API pages", async () => {
  const items = Array.from({ length: 125 }, (_, i) => ({ id: String(i) }));
  const fetchList = async ({ limit, offset }) => ({ total: items.length, items: items.slice(offset, offset + limit) });
  const fetchDetail = async (id) => ({
    job_status: "completed",
    predictions: [{ predicted_label: "occupied", effective_label: id === "110" ? "empty" : "occupied" }],
  });
  const result = await filterSnapshotsByOccupancy({}, "empty", fetchList, fetchDetail);
  assert.deepEqual(result, [{ id: "110" }]);
});

test("occupancy filtering refuses incomplete or oversized datasets", async () => {
  await assert.rejects(
    filterSnapshotsByOccupancy({}, "empty", async () => ({ total: 501, items: [] }), async () => ({})),
    /OCCUPANCY_FILTER_TOO_MANY/,
  );
  await assert.rejects(
    filterSnapshotsByOccupancy({}, "empty", async () => ({ total: 1, items: [{ id: "x" }] }), async () => { throw new Error("unavailable"); }),
    /unavailable/,
  );
});

test("CSV preserves predicted and verified labels and escapes formulas", () => {
  const csv = snapshotCsv({
    id: "id", captured_at: "2026-11-06T00:00:00Z",
    summary: { total: 1, empty: 1, occupied: 0, unknown: 0, occupancy_rate: 0 },
    predictions: [{ spot_code: "=P01", predicted_label: "occupied", effective_label: "empty", confidence: 0.8, model_version: "v1" }],
  }, "Camera");
  assert.match(csv, /"Dự đoán AI","Nhãn hiện tại"/);
  assert.match(csv, /"'=P01","occupied","empty","0.8"/);
});
