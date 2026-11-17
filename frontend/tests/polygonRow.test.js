import test from "node:test";
import assert from "node:assert/strict";
import { makePolygonRow, validatePolygonRow } from "../src/utils/polygonRow.js";

const square = [{ x: 0.1, y: 0.1 }, { x: 0.2, y: 0.1 }, { x: 0.2, y: 0.2 }, { x: 0.1, y: 0.2 }];

test("creates evenly shifted polygons without changing the source", () => {
  const copies = makePolygonRow(square, 2, 10, 0);
  assert.deepEqual(copies[0][0], { x: 0.2, y: 0.1 });
  assert.deepEqual(copies[1][0], { x: 0.3, y: 0.1 });
  assert.deepEqual(square[0], { x: 0.1, y: 0.1 });
  assert.equal(validatePolygonRow(copies, [square]), "");
});

test("rejects overlapping or out-of-image copies and invalid counts", () => {
  assert.match(validatePolygonRow(makePolygonRow(square, 2, 5, 0), [square]), /chồng nhau/);
  assert.match(validatePolygonRow(makePolygonRow(square, 1, -20, 0), [square]), /ngoài ảnh/);
  assert.deepEqual(makePolygonRow(square, 31, 10, 0), []);
});
