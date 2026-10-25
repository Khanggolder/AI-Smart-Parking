
import { useCallback, useEffect, useState } from "react";

import ResourceManager from "../components/ResourceManager";
import { DEMO_LOTS } from "../data/demoParking";

import {
  fetchParkingLots,
  fetchCameras,
  createCamera,
  updateCamera,
} from "../api/parking";

const DEMO_CAMERAS = [
  {
    id: "33333333-3333-4333-8333-333333333333",
    name: "CAM-01",
    parking_lot_id: DEMO_LOTS[0].id,
    config_version: 1,
  },
];

const fields = [
  {
    key: "name",
    label: "Tên camera",
    required: true,
  },
];

const columns = [
  { key: "name", label: "Tên camera" },
  { key: "config_version", label: "Phiên bản cấu hình" },
];

export default function Cameras({
  role = "operator",
  demo = false,
  demostate = "ready",
}) {
  const [lots, setLots] = useState(
    demo ? DEMO_LOTS : []
  );

  const [selectedLotId, setSelectedLotId] = useState(
    demo ? DEMO_LOTS[0].id : ""
  );

  const [loadingLots, setLoadingLots] = useState(!demo);
  const [error, setError] = useState("");

  useEffect(() => {
    if (demo) return;

    let active = true;

    fetchParkingLots()
      .then((data) => {
        if (!active) return;

        setLots(data);
        setSelectedLotId(data[0]?.id || "");
      })
      .catch(() => {
        if (active) {
          setError("Không tải được danh sách bãi xe.");
        }
      })
      .finally(() => {
        if (active) setLoadingLots(false);
      });

    return () => {
      active = false;
    };
  }, [demo]);

  const loadRows = useCallback(() => {
    return fetchCameras(selectedLotId);
  }, [selectedLotId]);

  return (
    <div className="manager-page">
      <section className="content-card">
        <h2>Chọn bãi xe</h2>

        {loadingLots && <p>Đang tải danh sách...</p>}
        {error && <p className="manager-error">{error}</p>}

        <select
          className="manager-select"
          value={selectedLotId}
          disabled={loadingLots || lots.length === 0}
          onChange={(e) => setSelectedLotId(e.target.value)}
        >
          {lots.length === 0 && (
            <option value="">Chưa có bãi xe</option>
          )}

          {lots.map((lot) => (
            <option key={lot.id} value={lot.id}>
              {lot.name}
            </option>
          ))}
        </select>
      </section>

      {selectedLotId && (
        <ResourceManager
          key={selectedLotId}
          title="Quản lý camera"
          fields={fields}
          columns={columns}
          role={role}
          demo={demo}
          initialRows={DEMO_CAMERAS.filter(
            (camera) =>
              camera.parking_lot_id === selectedLotId
          )}
          defaultValues={{
            parking_lot_id: selectedLotId,
          }}
          loadRows={loadRows}
          createItem={createCamera}
          updateItem={updateCamera}
          demoState={demostate}
        />
      )}
    </div>
  );
}
