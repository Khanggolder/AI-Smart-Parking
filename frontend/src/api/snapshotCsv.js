function csvCell(value) {
  let text = String(value ?? "");
  if (/^[\s]*[=+\-@\t\r]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}

export function snapshotCsv(snapshot, cameraName) {
  const rows = [
    ["Snapshot ID", "Camera", "Thời gian chụp (UTC)", "Tổng ô", "Ô trống", "Ô có xe", "Ô chưa xác định", "Tỷ lệ sử dụng (%)", "Mã ô", "Dự đoán AI", "Nhãn hiện tại", "Confidence", "Model"],
    ...snapshot.predictions.map((spot) => [
      snapshot.id, cameraName, snapshot.captured_at, snapshot.summary.total,
      snapshot.summary.empty, snapshot.summary.occupied, snapshot.summary.unknown,
      snapshot.summary.occupancy_rate, spot.spot_code,
      spot.predicted_label, spot.effective_label, spot.confidence, spot.model_version,
    ]),
  ];
  return "\uFEFF" + rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
}
