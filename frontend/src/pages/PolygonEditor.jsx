
import { useEffect, useRef, useState } from "react";
import { fetchCameras } from "../api/parking";
import { fetchCameraSpots, createSpot, updateSpot, deleteSpot } from "../api/spots";


const CAMERA_ID = "CAM-01";

function getStorageKey(file) {
  return [
    "asp-polygons-v1",
    CAMERA_ID,
    file.name,
    file.size,
    file.lastModified,
  ].join(":");
}



function isSelfIntersecting(points) {
  const cross = (a, b, c) =>
    (b.x - a.x) * (c.y - a.y) -
    (b.y - a.y) * (c.x - a.x);

  function onSegment(a, b, p) {
    const eps = 1e-9;

    return (
      Math.abs(cross(a, b, p)) < eps &&
      p.x >= Math.min(a.x, b.x) - eps &&
      p.x <= Math.max(a.x, b.x) + eps &&
      p.y >= Math.min(a.y, b.y) - eps &&
      p.y <= Math.max(a.y, b.y) + eps
    );
  }

  function intersects(a, b, c, d) {
    const abC = cross(a, b, c);
    const abD = cross(a, b, d);
    const cdA = cross(c, d, a);
    const cdB = cross(c, d, b);

    if (abC * abD < 0 && cdA * cdB < 0) {
      return true;
    }

    return (
      onSegment(a, b, c) ||
      onSegment(a, b, d) ||
      onSegment(c, d, a) ||
      onSegment(c, d, b)
    );
  }

  const n = points.length;

  for (let i = 0; i < n; i++) {
    const a = points[i];
    const b = points[(i + 1) % n];

    for (let j = i + 1; j < n; j++) {
      // Bỏ qua hai cạnh liền kề.
      if (
        j === i + 1 ||
        (i === 0 && j === n - 1)
      ) {
        continue;
      }

      const c = points[j];
      const d = points[(j + 1) % n];

      if (intersects(a, b, c, d)) {
        return true;
      }
    }
  }

  return false;
}


export default function PolygonEditor({ role = "operator", demo = false }) {
  const [imageUrl, setImageUrl] = useState("");
  const [draft, setDraft] = useState([]);
  const [polygons, setPolygons] = useState([]);
  const [message, setMessage] = useState("");
  const [cameras, setCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [loadingCameras, setLoadingCameras] = useState(!demo);
  const [cameraError, setCameraError] = useState("");
  const [storageKey, setStorageKey] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingPoints, setEditingPoints] = useState([]);
  const draggingIndex = useRef(null);
  const [cameraVersion, setCameraVersion] = useState(null);
  const [loadingSpots, setLoadingSpots] = useState(false);
  const [spotsError, setSpotsError] = useState("");
  const [saving, setSaving] = useState(false);

  const isAdmin = role === "admin";

  useEffect(() => {
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [imageUrl]);
  

  
useEffect(() => {
  if (demo) return;

  let active = true;

  fetchCameras()
    .then((data) => {
      if (!active) return;

      setCameras(data);
      setSelectedCameraId(data[0]?.id || "");
    })
    .catch((error) => {
      if (!active) return;

      setCameraError(
        error.response?.data?.error?.message ||
          "Không thể tải camera từ Backend."
      );
    })
    .finally(() => {
      if (active) setLoadingCameras(false);
    });

  return () => {
    active = false;
  };
}, [demo]);


useEffect(() => {
  if (demo || !selectedCameraId) return;

  let active = true;

  fetchCameraSpots(selectedCameraId)
    .then((data) => {
      if (!active) return;

      if (
        !Array.isArray(data?.items) ||
        !Number.isInteger(data?.camera_config_version)
      ) {
        throw new Error(
          "Dữ liệu polygon từ Backend không hợp lệ."
        );
      }

      setPolygons(data.items);
      setCameraVersion(data.camera_config_version);
      setSpotsError("");
    })
    .catch((error) => {
      if (!active) return;

      setSpotsError(
        error.response?.data?.error?.message ||
        error.message ||
        "Không thể tải polygon từ Backend."
      );
    })
    .finally(() => {
      if (active) setLoadingSpots(false);
    });

  return () => {
    active = false;
  };
}, [demo, selectedCameraId]);



  function handleImageChange(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!["image/jpeg", "image/png"].includes(file.type)) {
      setMessage("Chỉ hỗ trợ ảnh JPG hoặc PNG.");
      return;
    }

    if (
      imageUrl &&
      !window.confirm(
        "Đổi ảnh sẽ bỏ các thay đổi chưa lưu. Tiếp tục?"
      )
    ) {
      event.target.value = "";
      return;
    }

      if (!demo) {
    if (polygons.some((item) => item.pending)) {
      setMessage("Hãy lưu polygon đang chờ trước khi đổi ảnh.");
      event.target.value = "";
      return;
    }

    setImageUrl(URL.createObjectURL(file));
    setDraft([]);
    setEditingId(null);
    setEditingPoints([]);
    setMessage(
      "Đã chọn ảnh để vẽ. Ảnh chỉ dùng để căn tọa độ, chưa upload lên Backend."
    );
    return;
  }

    const key = getStorageKey(file);
    let savedPolygons = [];

    try {
      const savedData = localStorage.getItem(key);

      if (savedData) {
        const parsed = JSON.parse(savedData);

        if (!Array.isArray(parsed)) {
          throw new Error("Invalid saved data");
        }

        savedPolygons = parsed;
      }
    } catch {
      setMessage("Dữ liệu đã lưu không hợp lệ.");
      return;
    }

    setImageUrl(URL.createObjectURL(file));
    setStorageKey(key);

    setDraft([]);
    setPolygons(savedPolygons);
    setEditingId(null);
    setEditingPoints([]);
    draggingIndex.current = null;

    setMessage(
      savedPolygons.length > 0
        ? `Đã tải lại ${savedPolygons.length} polygon từ trình duyệt.`
        : "Đã tải ảnh. Bạn có thể bắt đầu vẽ polygon."
    );
  }

  function handleCanvasClick(event) {
      if (
        !isAdmin ||
        !imageUrl ||
        editingId !== null ||
        saving ||
        (!demo &&
          (cameraVersion === null ||
            !selectedCameraId ||
            polygons.some((item) => item.pending)))
      ) {
        return;
      }

    const rect = event.currentTarget.getBoundingClientRect();

    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;

    if (x < 0 || x > 1 || y < 0 || y > 1) return;

    setDraft((current) => [
      ...current,
      {
        x: Number(x.toFixed(4)),
        y: Number(y.toFixed(4)),
      },
    ]);

    setMessage("");
  }


    function finishPolygon() {

    if (!demo && polygons.some((item) => item.pending)) {
      setMessage("Hãy lưu polygon trước khi tạo polygon tiếp theo.");
      return;
    }

    if (draft.length > 50) {
      setMessage("Polygon chỉ được có tối đa 50 đỉnh.");
      return;
    }

    if (draft.length < 3) {
        setMessage("Polygon phải có ít nhất 3 đỉnh.");
        return;
    }

    const uniquePoints = new Set(
        draft.map((p) => `${p.x},${p.y}`)
    );

    if (uniquePoints.size !== draft.length) {
        setMessage("Polygon có đỉnh trùng nhau.");
        return;
    }

    const area = Math.abs(
        draft.reduce((sum, point, index) => {
        const next = draft[(index + 1) % draft.length];
        return sum + point.x * next.y - next.x * point.y;
        }, 0)
    ) / 2;

    if (area < 0.000001) {
        setMessage("Polygon có diện tích quá nhỏ hoặc bằng 0.");
        return;
    }

    if (isSelfIntersecting(draft)) {
        setMessage(
        "Polygon không hợp lệ: Các cạnh đang cắt nhau."
        );
        return;
    }

    const nextNumber =
      Math.max(
        0,
        ...polygons.map((item) => {
          const number = Number(
            item.spot_code.replace(/^P/, "")
          );
          return Number.isFinite(number) ? number : 0;
        })
      ) + 1;

    setPolygons((current) => [
        ...current,
        {
        id: crypto.randomUUID(),
        spot_code: `P${String(nextNumber).padStart(2, "0")}`,
        polygon: draft,
        pending: !demo,
        },
    ]);

    setDraft([]);
    setMessage("Đã tạo polygon hợp lệ.");
    }

  function undoPoint() {
    setDraft((current) => current.slice(0, -1));
  }

  

async function deletePolygon(id) {
  if (
    !isAdmin ||
    saving ||
    editingId !== null ||
    draft.length > 0
  ) {
    return;
  }

  const item = polygons.find((polygon) => polygon.id === id);
  if (!item) return;

  // Chế độ DEV: giữ nguyên hành vi xóa trong trình duyệt.
  if (demo) {
    setPolygons((current) =>
      current.filter((polygon) => polygon.id !== id)
    );
    setMessage("Đã xóa polygon khỏi bản nháp.");
    return;
  }

  // Chế độ Backend: chỉ xóa polygon đã lưu.
  if (
    item.pending ||
    !selectedCameraId ||
    cameraVersion === null
  ) {
    setMessage("Polygon chưa sẵn sàng để xóa.");
    return;
  }

  const confirmed = window.confirm(
    `Bạn có chắc muốn ngừng kích hoạt ${item.spot_code}?`
  );

  if (!confirmed) return;

  setSaving(true);
  setMessage("");

  try {
    await deleteSpot(id, cameraVersion);

    // GET mặc định chỉ trả về các polygon đang hoạt động.
    setPolygons((current) =>
      current.filter((polygon) => polygon.id !== id)
    );

    // Backend tăng config_version sau khi xóa thành công.
    setCameraVersion((current) => current + 1);

    setMessage(
      `Đã ngừng kích hoạt ${item.spot_code} trong PostgreSQL.`
    );
  } catch (error) {
    const code = error.response?.data?.error?.code;

    if (code === "CAMERA_VERSION_CONFLICT") {
      setMessage(
        "Cấu hình camera đã thay đổi. " +
        "Hãy nhấn F5 để lấy phiên bản mới nhất."
      );
    } else {
      setMessage(
        error.response?.data?.error?.message ||
        "Không thể xóa polygon trên Backend."
      );
    }
  } finally {
    setSaving(false);
  }
}


    function cancelDraft() {
    setDraft([]);
    setMessage("Đã hủy polygon đang vẽ.");
    }

    
function startEditPolygon(item) {
  if (!isAdmin) return;

  setDraft([]);
  setEditingId(item.id);
  setEditingPoints(item.polygon.map((point) => ({ ...point })));
  setMessage(`Đang chỉnh sửa ${item.spot_code}. Kéo các đỉnh màu cam.`);
}

function cancelEditPolygon() {
  setEditingId(null);
  setEditingPoints([]);
  draggingIndex.current = null;
  setMessage("Đã hủy chỉnh sửa. Polygon giữ nguyên.");
}

function moveVertex(event, index) {
  if (draggingIndex.current !== index) return;

  const svg = event.currentTarget.ownerSVGElement;
  if (!svg) return;

  const rect = svg.getBoundingClientRect();

  const x = Math.max(
    0,
    Math.min(1, (event.clientX - rect.left) / rect.width)
  );

  const y = Math.max(
    0,
    Math.min(1, (event.clientY - rect.top) / rect.height)
  );

  setEditingPoints((current) =>
    current.map((point, i) =>
      i === index
        ? {
            x: Number(x.toFixed(4)),
            y: Number(y.toFixed(4)),
          }
        : point
    )
  );
}


async function saveEditPolygon() {
  if (!editingId || !isAdmin || saving) return;

  if (
    !demo &&
    (!selectedCameraId || cameraVersion === null)
  ) {
    setMessage("Chưa tải xong cấu hình camera.");
    return;
  }

  if (
    editingPoints.length < 3 ||
    editingPoints.length > 50
  ) {
    setMessage("Polygon phải có từ 3 đến 50 đỉnh.");
    return;
  }

  const uniquePoints = new Set(
    editingPoints.map((point) => `${point.x},${point.y}`)
  );

  if (uniquePoints.size !== editingPoints.length) {
    setMessage("Polygon có các đỉnh trùng nhau.");
    return;
  }

  const area =
    Math.abs(
      editingPoints.reduce((sum, point, index) => {
        const next =
          editingPoints[(index + 1) % editingPoints.length];

        return (
          sum +
          point.x * next.y -
          next.x * point.y
        );
      }, 0)
    ) / 2;

  if (area < 0.000001) {
    setMessage("Polygon có diện tích quá nhỏ hoặc bằng 0.");
    return;
  }

  if (isSelfIntersecting(editingPoints)) {
    setMessage(
      "Không thể lưu: Các cạnh polygon đang cắt nhau."
    );
    return;
  }

  const pointsToSave = editingPoints.map(
    (point) => ({ ...point })
  );

  // Chế độ DEV: giữ chức năng cũ, chưa gọi API.
  if (demo) {
    setPolygons((current) =>
      current.map((item) =>
        item.id === editingId
          ? { ...item, polygon: pointsToSave }
          : item
      )
    );

    setEditingId(null);
    setEditingPoints([]);
    draggingIndex.current = null;
    setMessage("Đã lưu chỉnh sửa vào bản nháp.");
    return;
  }

  // Chế độ Backend: gửi PATCH đến PostgreSQL.
  setSaving(true);
  setMessage("");

  try {
    const updated = await updateSpot(
      editingId,
      pointsToSave,
      cameraVersion
    );

    setPolygons((current) =>
      current.map((item) =>
        item.id === editingId ? updated : item
      )
    );

    setCameraVersion(updated.camera_config_version);

    setEditingId(null);
    setEditingPoints([]);
    draggingIndex.current = null;

    setMessage(
      `Đã cập nhật ${updated.spot_code} vào PostgreSQL thành công.`
    );
  } catch (error) {
    const code = error.response?.data?.error?.code;

    if (code === "CAMERA_VERSION_CONFLICT") {
      setMessage(
        "Cấu hình camera đã thay đổi trên Backend. " +
        "Vui lòng tải lại trang trước khi chỉnh sửa tiếp."
      );
    } else {
      setMessage(
        error.response?.data?.error?.message ||
        "Không thể cập nhật polygon lên PostgreSQL."
      );
    }
  } finally {
    setSaving(false);
  }
}



  async function savePendingPolygon() {
    if (!isAdmin || demo || saving) return;

    if (!selectedCameraId || cameraVersion === null) {
      setMessage("Chưa chọn camera hoặc chưa tải xong cấu hình.");
      return;
    }

    if (draft.length > 0 || editingId !== null) {
      setMessage("Hãy hoàn thành hoặc hủy thao tác đang thực hiện.");
      return;
    }

    const pending = polygons.filter((item) => item.pending);

    if (pending.length !== 1) {
      setMessage("Hãy hoàn thành một polygon trước khi lưu.");
      return;
    }

    const item = pending[0];

    setSaving(true);
    setMessage("");

    try {
      const saved = await createSpot(
        selectedCameraId,
        item.spot_code,
        item.polygon,
        cameraVersion
      );

      setPolygons((current) =>
        current.map((polygon) =>
          polygon.id === item.id ? saved : polygon
        )
      );

      setCameraVersion(saved.camera_config_version);

      setMessage(
        `Đã lưu ${saved.spot_code} vào PostgreSQL thành công.`
      );
    } catch (error) {
      if (error.response?.status === 409) {
        setMessage(
          "Xung đột dữ liệu hoặc mã ô đỗ đã tồn tại. " +
          "Kiểm tra thông báo API và tải lại cấu hình nếu phiên bản đã thay đổi."
        );
      } else {
        setMessage(
          error.response?.data?.error?.message ||
            "Không thể lưu polygon lên PostgreSQL."
        );
      }
    } finally {
      setSaving(false);
    }
  }

  
  function savePolygons() {
    if (!isAdmin || !storageKey) {
      setMessage("Vui lòng chọn ảnh trước khi lưu.");
      return;
    }

    if (editingId !== null || draft.length > 0) {
      setMessage(
        "Hãy hoàn thành hoặc hủy thao tác đang thực hiện trước khi lưu."
      );
      return;
    }

    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify(polygons)
      );

      setMessage(
        `Đã lưu ${polygons.length} polygon vào trình duyệt. ` +
        "Chưa lưu lên Backend."
      );
    } catch {
      setMessage("Không thể lưu dữ liệu vào trình duyệt.");
    }
  }

  function toSvgPoints(points) {
    return points
      .map((point) => `${point.x * 1000},${point.y * 1000}`)
      .join(" ");
  }

  return (
    <section className="content-card polygon-editor">
      <h2>Polygon Editor</h2>
      
      {!demo && (
        <div className="polygon-controls">
          <label htmlFor="polygon-camera">
            Chọn camera từ PostgreSQL:
          </label>

          <select
            id="polygon-camera"
            className="manager-select"
            value={selectedCameraId}
            disabled={loadingCameras || saving}
            onChange={(event) => {
              const cameraId = event.target.value;

              setSelectedCameraId(cameraId);
              setPolygons([]);
              setCameraVersion(null);
              setSpotsError("");
              setLoadingSpots(Boolean(cameraId));
              setDraft([]);
              setEditingId(null);
              setEditingPoints([]);
              setImageUrl("");
              setMessage("");
            }}
          >
            <option value="">-- Chọn camera --</option>

            {cameras.map((camera) => (
              <option key={camera.id} value={camera.id}>
                {camera.name}
              </option>
            ))}
          </select>

          {loadingCameras && <p>Đang tải camera...</p>}

          {cameraError && (
            <p className="manager-error" role="alert">
              {cameraError}
            </p>
          )}

          {!loadingCameras &&
            !cameraError &&
            cameras.length === 0 && (
              <p>Chưa có camera trong PostgreSQL.</p>
            )}

          {selectedCameraId && (
            <p>
              Camera UUID: <code>{selectedCameraId}</code>
            </p>
          )}
        </div>
      )}


      <p>
        Camera:{" "}
        {demo
          ? "CAM-01"
          : cameras.find(
              (camera) => camera.id === selectedCameraId
            )?.name || "Chưa chọn camera"}
        {" · "}
        {isAdmin ? "Admin" : "Operator"}
      </p>

      <p className="manager-demo">
        {demo
          ? "Chế độ DEV: Polygon lưu bằng localStorage."
          : "Chế độ Backend: Danh sách polygon tải từ PostgreSQL. Chưa hỗ trợ ghi tại bước này."}
      </p>

      {isAdmin && demo && (
        <div className="polygon-controls">
          <label>
            Chọn ảnh tham chiếu:
            <input
              type="file"
              accept="image/*"
              onChange={handleImageChange}
            />
          </label>

          <button
            type="button"
            onClick={undoPoint}
            disabled={draft.length === 0}
          >
            Hoàn tác điểm
          </button>

            <button
            type="button"
            onClick={cancelDraft}
            disabled={draft.length === 0}
            >
            Hủy polygon đang vẽ
            </button>

          <button
            type="button"
            onClick={finishPolygon}
            disabled={!imageUrl}
          >
            Hoàn thành polygon
          </button>

          
          <button
            type="button"
            onClick={savePolygons}
            disabled={!imageUrl || editingId !== null}
            className="polygon-save-button"
          >
            Lưu cấu hình polygon
          </button>

        </div>
      )}

      
    {isAdmin && !demo && (
      <div className="polygon-controls">
        <label>
          Chọn ảnh để vẽ polygon:
          <input
            type="file"
            accept="image/png,image/jpeg"
            onChange={handleImageChange}
            disabled={
              !selectedCameraId ||
              cameraVersion === null ||
              saving
            }
          />
        </label>

        <button
          type="button"
          onClick={undoPoint}
          disabled={draft.length === 0 || saving}
        >
          Hoàn tác điểm
        </button>

        <button
          type="button"
          onClick={cancelDraft}
          disabled={draft.length === 0 || saving}
        >
          Hủy polygon đang vẽ
        </button>

        <button
          type="button"
          onClick={finishPolygon}
          disabled={
            !imageUrl ||
            saving ||
            polygons.some((item) => item.pending)
          }
        >
          Hoàn thành polygon
        </button>

        <button
          type="button"
          className="polygon-save-button"
          onClick={savePendingPolygon}
          disabled={
            saving ||
            draft.length > 0 ||
            !polygons.some((item) => item.pending)
          }
        >
          {saving ? "Đang lưu..." : "Lưu lên PostgreSQL"}
        </button>
      </div>
    )}

      {message && <p role="status">{message}</p>}

      {imageUrl ? (
        <div className="polygon-canvas">
          <img
            src={imageUrl}
            alt="Ảnh tham chiếu bãi xe"
          />

          <svg
            className="polygon-overlay"
            viewBox="0 0 1000 1000"
            preserveAspectRatio="none"
            onClick={handleCanvasClick}
            role="img"
            aria-label="Vùng vẽ polygon"
          >

        {polygons.map((item) => (
          <polygon
            key={item.id}
            points={toSvgPoints(
              item.id === editingId
                ? editingPoints
                : item.polygon
            )}
            fill={
              item.id === editingId
                ? "rgba(245,158,11,0.25)"
                : "rgba(34,197,94,0.25)"
            }
            stroke={
              item.id === editingId
                ? "#f59e0b"
                : "#22c55e"
            }
            strokeWidth="4"
            vectorEffect="non-scaling-stroke"
          />
        ))}

        {editingId !== null &&
          editingPoints.map((point, index) => (
            <circle
              key={index}
              cx={point.x * 1000}
              cy={point.y * 1000}
              r="10"
              fill="#f59e0b"
              stroke="#ffffff"
              strokeWidth="3"
              className="polygon-vertex"
              onPointerDown={(event) => {
                event.preventDefault();
                event.stopPropagation();
                draggingIndex.current = index;
                event.currentTarget.setPointerCapture(
                  event.pointerId
                );
              }}
              onPointerMove={(event) => {
                moveVertex(event, index);
              }}
              onPointerUp={() => {
                draggingIndex.current = null;
              }}
              onPointerCancel={() => {
                draggingIndex.current = null;
              }}
              onClick={(event) => event.stopPropagation()}
            />
          ))}


            <polyline
              points={toSvgPoints(draft)}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="3"
              vectorEffect="non-scaling-stroke"
            />

            {draft.map((point, index) => (
              <circle
                key={index}
                cx={point.x * 1000}
                cy={point.y * 1000}
                r="7"
                fill="#f59e0b"
              />
            ))}
          </svg>
        </div>
      ) : (
        <div className="manager-state">
          <h3>Chưa có ảnh tham chiếu</h3>
          <p>Admin hãy chọn ảnh để bắt đầu vẽ ô đỗ.</p>
        </div>
      )}

      {!demo && (
  <>
    {cameraVersion !== null && (
      <p>Camera config version: {cameraVersion}</p>
    )}

    {loadingSpots && <p>Đang tải polygon...</p>}

    {spotsError && (
      <p className="manager-error" role="alert">
        {spotsError}
      </p>
    )}
  </>
)}
      <h3>Danh sách polygon ({polygons.length})</h3>




      {editingId !== null && (
        <div className="polygon-edit-actions">
          <button
            type="button"
            onClick={saveEditPolygon}
            disabled={saving}
          >
            {saving
              ? "Đang cập nhật..."
              : demo
                ? "Lưu chỉnh sửa"
                : "Lưu chỉnh sửa lên PostgreSQL"}
          </button>

          <button
            type="button"
            onClick={cancelEditPolygon}
            disabled={saving}
          >
            Hủy chỉnh sửa
          </button>
        </div>
      )}


      {polygons.map((item) => (
        <div key={item.id} className="polygon-list-item">
          <span>
            {item.spot_code}: {item.polygon.length} đỉnh
            {item.pending ? " . Chưa lưu" : ""}
          </span>


          {isAdmin && (
            <div className="polygon-list-actions">
              <button
                type="button"
                onClick={() => startEditPolygon(item)}
                disabled={
                  saving ||
                  editingId !== null ||
                  draft.length > 0 ||
                  polygons.some((polygon) => polygon.pending)
                }
                className="polygon-edit-button"
              >
                Sửa
              </button>


              <button
                type="button"
                onClick={() => deletePolygon(item.id)}
                disabled={
                  saving ||
                  editingId !== null ||
                  draft.length > 0 ||
                  (!demo &&
                    (cameraVersion === null || item.pending))
                }
              >
                {demo ? "Xóa" : "Ngừng kích hoạt"}
              </button>

            </div>
          )}
        </div>
      ))}

    </section>
  );
}
