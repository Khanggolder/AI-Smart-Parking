import test from "node:test";
import assert from "node:assert/strict";
import { waitForVideoSnapshot } from "../src/utils/videoJobs.js";

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
