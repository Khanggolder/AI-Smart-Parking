export function validateReferenceTarget(camera, spots) {
  if (!camera || !Array.isArray(spots?.items) || !Number.isInteger(spots?.camera_config_version)) {
    return "Không tải được cấu hình camera. Hãy thử lại.";
  }
  if (spots.camera_config_version !== camera.config_version) {
    return "Cấu hình camera đã thay đổi. Hãy tải lại danh sách camera và thử lại.";
  }
  if (spots.items.some((spot) => spot.is_active)) {
    return "Camera đang có ô đỗ hoạt động. Không thể thay ảnh tham chiếu; hãy chọn camera khác hoặc ngừng kích hoạt các ô trước.";
  }
  return "";
}
