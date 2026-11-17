import test from "node:test";
import assert from "node:assert/strict";
import { captureTime, validateVideoCamera, waitBeforeNextFrame, waitForVideoSnapshot } from "../src/utils/videoJobs.js";

test("checks camera dimensions before creating snapshots", () => {
  assert.match(validateVideoCamera({}, { videoWidth: 1100, videoHeight: 720 }), /chưa có ảnh tham chiếu/);
  assert.match(validateVideoCamera({ reference_width: 640, reference_height: 480 }, { videoWidth: 1100, videoHeight: 720 }), /kích thước/);
  assert.equal(validateVideoCamera({ reference_width: 1100, reference_height: 720 }, { videoWidth: 1100, videoHeight: 720 }), "");
});

test("derives frame time and rejects implausible future times in production", () => {
  assert.equal(captureTime(0, 12, true, 20_000), "1970-01-01T00:00:12.000Z");
  assert.throws(() => captureTime(0, 100, true, 20_000), /tương lai/);
  assert.equal(captureTime(0, 100, false, 20_000), "1970-01-01T00:01:40.000Z");
});

test("waits until the submitted snapshot completes", async () => {
  const statuses = ["processing", "completed"];
  const seen = [];
  const result = await waitForVideoSnapshot({ id: "one", job_status: "queued" }, {
    getSnapshot: async (id) => { seen.push(id); return { id, job_status: statuses.shift() }; },
    wait: async () => {},
  });
  assert.equal(result.job_status, "completed");
  assert.deepEqual(seen, ["one", "one"]);
});

test("stops on failure and marks lost job status as uncertain", async () => {
  await assert.rejects(waitForVideoSnapshot({ id: "one", job_status: "failed", error_code: "AI_UNAVAILABLE" }, { getSnapshot: async () => {}, wait: async () => {} }), /AI_UNAVAILABLE/);
  await assert.rejects(waitForVideoSnapshot({ id: "one", job_status: "queued" }, { getSnapshot: async () => { throw new Error("network"); }, wait: async () => {} }), (error) => error.uncertain === true);
  await assert.rejects(waitForVideoSnapshot({ id: "one", job_status: "queued" }, { getSnapshot: async () => ({}), wait: async () => {}, now: () => 1, timeout: 0 }), (error) => error.uncertain === true);
});

test("stopping during the interval prevents another frame from being scheduled", async () => {
  let time = 0;
  let stopped = false;
  const result = await waitBeforeNextFrame({ intervalMs: 5000, now: () => time, shouldStop: () => stopped, wait: async (ms) => { time += ms; stopped = true; } });
  assert.equal(result, false);
  assert.equal(time, 250);
});

test("finished failed AI job is surfaced without pretending it succeeded", async () => {
  const statuses = [{ id: "x", job_status: "processing" }, { id: "x", job_status: "failed", error_code: "AI_UNAVAILABLE" }];
  await assert.rejects(waitForVideoSnapshot({ id: "x", job_status: "queued" }, { getSnapshot: async () => statuses.shift(), wait: async () => {} }), /AI_UNAVAILABLE/);
});

test("frame timestamps use video offset and preserve the submitted real starting time", () => {
  const base = Date.parse("2026-11-17T12:30:00+07:00");
  assert.equal(captureTime(base, 12.5, true, base + 20_000), "2026-11-17T05:30:12.500Z");
});
