import { DEMO_LOTS } from "../data/demoParking";
import ResourceManager from "../components/ResourceManager";

import {
  fetchParkingLots,
  createParkingLot,
  updateParkingLot,
} from "../api/parking";


const fields = [
  {
    key: "name",
    label: "Tên bãi xe",
    required: true,
  },
  {
    key: "description",
    label: "Mô tả",
    required: false,
  },
];

const columns = [
  { key: "name", label: "Tên bãi xe" },
  { key: "description", label: "Mô tả" },
];

export default function ParkingLots({
  role = "operator",
  demo = false,
  demostate = "ready",
}) {
  return (
    <ResourceManager
      title="Quản lý bãi xe"
      fields={fields}
      columns={columns}
      role={role}
      demo={demo}
      initialRows={DEMO_LOTS}
      loadRows={fetchParkingLots}
      createItem={createParkingLot}
      updateItem={updateParkingLot}
      demoState={demostate}
    />
  );
}
