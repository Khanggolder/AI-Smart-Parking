
import StatCard from "../components/StatCard";

function Dashboard() {
  // Dữ liệu giả lập, chưa kết nối Backend/AI
  const stats = [
    {
      title: "Tổng số ô",
      value: 100,
      color: "#2563eb",
    },
    {
      title: "Ô trống",
      value: 35,
      color: "#16a34a",
    },
    {
      title: "Đã có xe",
      value: 60,
      color: "#dc2626",
    },
    {
      title: "Chưa xác định",
      value: 5,
      color: "#ca8a04",
    },
  ];

  const occupancyRate = (
    (stats[2].value / stats[0].value) * 100
  ).toFixed(1);

  return (
    <>
      <div className="stats-grid">
        {stats.map((item) => (
          <StatCard
            key={item.title}
            title={item.title}
            value={item.value}
            color={item.color}
          />
        ))}
      </div>

      <section className="content-card">
        <h2>Giám sát bãi đỗ xe</h2>

        <p>Camera: CAM-01</p>

        <p>
          Tỷ lệ lấp đầy: {occupancyRate}%
        </p>

        <p>
          Có 5 ô chưa xác định.
          Chưa thể kết luận bãi xe đã đầy.
        </p>

        <p>
          Dữ liệu hiện tại chỉ phục vụ
          thử nghiệm giao diện.
        </p>
      </section>
    </>
  );
}

export default Dashboard;
