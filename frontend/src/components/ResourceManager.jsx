
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

  if (!error.response && error.code === "ERR_NETWORK") {
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
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({});
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const isAdmin = role === "admin";

  useEffect(() => {
    if (demo) return;

    let active = true;

    loadRows()
      .then((data) => {
        if (active) setRows(data);
      })
      .catch((err) => {
        if (active) setError(getErrorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [demo, loadRows]);

  function startCreate() {
    setEditingId(null);
    setForm({});
    setError("");
    setShowForm(true);
  }

  function startEdit(row) {
    setEditingId(row.id);

    const values = {};
    fields.forEach((field) => {
      values[field.key] = row[field.key] ?? "";
    });

    setForm(values);
    setError("");
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
    setError("");
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
          ? "Đã cập nhật dữ liệu mẫu (không lưu Backend)."
          : "Đã lưu dữ liệu thành công."
      );
      setShowForm(false);
      setEditingId(null);
    } catch (err) {
      setError(getErrorMessage(err));
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
          DEV PREVIEW – Dữ liệu giả lập, không gọi Backend
        </p>
      )}

      <div className="manager-toolbar">
        <h2>{title}</h2>

        {isAdmin && (
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
          ? "Quyền Admin: xem, thêm và chỉnh sửa."
          : "Quyền Operator: chỉ xem dữ liệu."}
      </p>

      {loading && <p>Đang tải dữ liệu...</p>}
      {error && (
        <p className="manager-error" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="manager-success">{message}</p>
      )}

      {!loading && (
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
              {rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={
                      columns.length + (isAdmin ? 1 : 0)
                    }
                  >
                    Chưa có dữ liệu.
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
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
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {showForm && isAdmin && (
        <form
          className="manager-form"
          onSubmit={handleSubmit}
        >
          <h3>
            {editingId !== null
              ? "Chỉnh sửa"
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
              disabled={saving}
              type="submit"
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
        API xóa bãi xe/camera chưa có trong Backend
        Contract v1. Nút xóa chỉ xuất hiện trong
        chế độ demo.
      </p>
    </section>
  );
}
