import test from "node:test";
import assert from "node:assert/strict";
import { validateReferenceTarget } from "../src/utils/videoReference.js";

test("allows reference upload only for a current camera with no active spots", () => {
  const camera = { id: "cam", config_version: 7 };
  assert.equal(validateReferenceTarget(camera, { camera_config_version: 7, items: [{ is_active: false }] }), "");
  assert.match(validateReferenceTarget(camera, { camera_config_version: 7, items: [{ is_active: true }] }), /đang có ô đỗ hoạt động/);
  assert.match(validateReferenceTarget(camera, { camera_config_version: 8, items: [] }), /đã thay đổi/);
  assert.match(validateReferenceTarget(camera, null), /Không tải được/);
});
