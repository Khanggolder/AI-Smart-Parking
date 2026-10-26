
import { useEffect, useState } from "react";

function getErrorMessage(error) {
  if (error.response?.status === 401) {
    return "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.";
  }

  if (error.response?.status === 403) {
    return "Bạn không có quyền thực hiện thao tác này.";
  }

  if (error.response?.data?.error?.message) {
    return error.response.data.error.message;
  }

  if (error.code === "ERR_NETWORK") {
    return "Không kết nối được Backend. Hãy kiểm tra API.";
  }

  return error.message || "Đã xảy ra lỗi.";
}

export default function ResourceManager({
  title,
  fields,
  columns,
  role,
  demo = false,
  demoState = "ready",
  initialRows = [],
  loadRows,
  createItem,
  updateItem,
  defaultValues = {},
}) {
  const [rows, setRows] = useState(
    demo ? initialRows : []
  );

  const [loading, setLoading] = useState(!demo);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [retryKey, setRetryKey] = useState(0);

  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({});
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState("");

  const isAdmin = role === "admin";

  useEffect(() => {
    if (demo) return;

    let active = true;

    loadRows()
      .then((data) => {
        if (!active) return;

        setRows(data);
        setLoadError("");
      })
      .catch((error) => {
        if (active) {
          setLoadError(getErrorMessage(error));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [demo, loadRows, retryKey]);

  // Chỉ giả lập trạng thái khi chạy DEV Preview.
  const previewState = demo ? demoState : "ready";

  const isLoading =
    previewState === "loading" ||
    (!demo && loading);

  const displayError =
    previewState === "error"
      ? "Không tải được dữ liệu (lỗi giả lập để kiểm thử)."
      : loadError;

  const visibleRows =
    previewState === "empty" ? [] : rows;

  const isReady = !isLoading && !displayError;

  function handleRetry() {
    if (demo) return;

    setLoading(true);
    setLoadError("");
    setRetryKey((value) => value + 1);
  }

  function startCreate() {
    setEditingId(null);
    setForm({});
    setActionError("");
    setMessage("");
    setShowForm(true);
  }

  function startEdit(row) {
    const values = {};

    fields.forEach((field) => {
      values[field.key] = row[field.key] ?? "";
    });

    setEditingId(row.id);
    setForm(values);
    setActionError("");
    setMessage("");
    setShowForm(true);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!isAdmin) return;

    const payload = {};

    fields.forEach((field) => {
      payload[field.key] = String(
        form[field.key] ?? ""
      ).trim();
    });

    setSaving(true);
    setActionError("");
    setMessage("");

    try {
      if (demo) {
        if (editingId !== null) {
          setRows((current) =>
            current.map((row) =>
              row.id === editingId
                ? { ...row, ...payload }
                : row
            )
          );
        } else {
          setRows((current) => [
            ...current,
            {
              ...defaultValues,
              ...payload,
              id: crypto.randomUUID(),
            },
          ]);
        }
      } else {
        if (editingId !== null) {
          await updateItem(editingId, payload);
        } else {
          await createItem({
            ...defaultValues,
            ...payload,
          });
        }

        setRows(await loadRows());
      }

      setMessage(
        demo
          ? "Đã cập nhật dữ liệu mẫu, không lưu Backend."
          : "Lưu dữ liệu thành công."
      );

      setShowForm(false);
      setEditingId(null);
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  function deleteDemo(id) {
    if (!demo || !isAdmin) return;

    if (!window.confirm("Xóa mục này khỏi dữ liệu demo?")) {
      return;
    }

    setRows((current) =>
      current.filter((row) => row.id !== id)
    );

    setMessage("Đã xóa khỏi dữ liệu demo.");
  }

  return (
    <section className="content-card manager">
      {demo && (
        <p className="manager-demo">
          DEV PREVIEW – Không gọi Backend
        </p>
      )}

      <div className="manager-toolbar">
        <h2>{title}</h2>

        {isAdmin && isReady && (
          <button
            className="manager-primary"
            type="button"
            onClick={startCreate}
          >
            + Thêm mới
          </button>
        )}
      </div>

      <p className="manager-hint">
        {isAdmin
          ? "Admin: xem, thêm và chỉnh sửa."
          : "Operator: chỉ xem dữ liệu."}
      </p>

      {message && (
        <p className="manager-success" role="status">
          {message}
        </p>
      )}

      {actionError && (
        <p className="manager-error" role="alert">
          {actionError}
        </p>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="manager-state" role="status">
          <div
            className="manager-spinner"
            aria-hidden="true"
          />

          <h3>Đang tải dữ liệu...</h3>
          <p>Vui lòng chờ hệ thống xử lý.</p>
        </div>
      )}

      {/* Error */}
      {!isLoading && displayError && (
        <div className="manager-state" role="alert">
          <div className="manager-state-icon">
            !
          </div>

          <h3>Không thể tải dữ liệu</h3>
          <p>{displayError}</p>

          {!demo && (
            <button
              type="button"
              className="manager-primary"
              onClick={handleRetry}
            >
              Thử lại
            </button>
          )}
        </div>
      )}

      {/* Empty */}
      {isReady && visibleRows.length === 0 && (
        <div className="manager-state" role="status">
          <div className="manager-state-icon">
            ∅
          </div>

          <h3>Chưa có dữ liệu</h3>

          <p>
            Danh sách hiện đang trống.
            {isAdmin
              ? " Bạn có thể thêm mục mới."
              : " Vui lòng liên hệ Admin nếu cần cập nhật."}
          </p>
        </div>
      )}

      {/* Data table */}
      {isReady && visibleRows.length > 0 && (
        <div className="manager-table-wrap">
          <table className="manager-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.key}>
                    {column.label}
                  </th>
                ))}

                {isAdmin && <th>Thao tác</th>}
              </tr>
            </thead>

            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.id}>
                  {columns.map((column) => (
                    <td key={column.key}>
                      {row[column.key] ?? "—"}
                    </td>
                  ))}

                  {isAdmin && (
                    <td className="manager-actions">
                      <button
                        type="button"
                        onClick={() => startEdit(row)}
                      >
                        Sửa
                      </button>

                      {demo && (
                        <button
                          type="button"
                          onClick={() =>
                            deleteDemo(row.id)
                          }
                        >
                          Xóa demo
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit form */}
      {showForm && isAdmin && isReady && (
        <form
          className="manager-form"
          onSubmit={handleSubmit}
        >
          <h3>
            {editingId !== null
              ? "Chỉnh sửa thông tin"
              : "Thêm mới"}
          </h3>

          {fields.map((field) => (
            <label key={field.key}>
              {field.label}

              <input
                type="text"
                required={field.required}
                maxLength={field.maxLength || 150}
                value={form[field.key] ?? ""}
                placeholder={field.placeholder || ""}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    [field.key]: event.target.value,
                  }))
                }
              />
            </label>
          ))}

          <div className="manager-actions">
            <button
              className="manager-primary"
              type="submit"
              disabled={saving}
            >
              {saving ? "Đang lưu..." : "Lưu"}
            </button>

            <button
              type="button"
              disabled={saving}
              onClick={() => setShowForm(false)}
            >
              Hủy
            </button>
          </div>
        </form>
      )}

      <p className="manager-hint">
        Chức năng xóa bãi xe/camera chỉ dùng
        trong DEV Preview, chưa có API thật.
      </p>
    </section>
  );
}
