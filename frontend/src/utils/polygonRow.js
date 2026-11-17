export function makePolygonRow(polygon, count, dx, dy) {
  if (!Number.isInteger(count) || count < 1 || count > 30 || !Number.isFinite(dx) || !Number.isFinite(dy)) return [];
  return Array.from({ length: count }, (_, index) => polygon.map(({ x, y }) => ({
    x: Number((x + (index + 1) * dx / 100).toFixed(4)),
    y: Number((y + (index + 1) * dy / 100).toFixed(4)),
  })));
}

export function validatePolygonRow(copies, existing) {
  if (!copies.length || copies.some((copy) => copy.length < 3 || copy.some(({ x, y }) => x < 0 || x > 1 || y < 0 || y > 1))) return "Một số ô vượt ngoài ảnh hoặc không hợp lệ.";
  const boxes = existing.map(bounds);
  for (const copy of copies) {
    const box = bounds(copy);
    if (boxes.some((other) => overlaps(box, other))) return "Khung bao các ô đang chồng nhau. Hãy kiểm tra và điều chỉnh khoảng cách.";
    boxes.push(box);
  }
  return "";
}

function bounds(points) {
  return { left: Math.min(...points.map((p) => p.x)), right: Math.max(...points.map((p) => p.x)), top: Math.min(...points.map((p) => p.y)), bottom: Math.max(...points.map((p) => p.y)) };
}

function overlaps(a, b) {
  const tolerance = 0.00001;
  return a.left < b.right - tolerance && a.right > b.left + tolerance && a.top < b.bottom - tolerance && a.bottom > b.top + tolerance;
}
