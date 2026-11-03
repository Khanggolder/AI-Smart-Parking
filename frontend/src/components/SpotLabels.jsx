export default function SpotLabels({ spots }) {
  return spots.map((spot) => {
    if (!spot.polygon?.length) return null;
    const x = Math.min(96, Math.max(4, spot.polygon.reduce((sum, p) => sum + p.x, 0) / spot.polygon.length * 100));
    const y = Math.min(96, Math.max(4, spot.polygon.reduce((sum, p) => sum + p.y, 0) / spot.polygon.length * 100));
    return <span key={spot.id} className="polygon-label" style={{ left: `${x}%`, top: `${y}%` }}>{spot.spot_code}</span>;
  });
}
