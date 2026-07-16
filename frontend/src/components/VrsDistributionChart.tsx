interface VrsDistributionChartProps {
  distribution: Record<string, number>;
}

/** Single-series magnitude across ordered buckets -> one sequential hue
 * (the skill's default blue, --series-1), not a categorical/status palette. */
export function VrsDistributionChart({ distribution }: VrsDistributionChartProps) {
  const entries = Object.entries(distribution);
  const max = Math.max(1, ...entries.map(([, n]) => n));

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 12, height: 120 }}>
      {entries.map(([bucket, count]) => (
        <div key={bucket} style={{ flex: 1, textAlign: "center" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 4 }}>{count}</div>
          <div
            style={{
              height: `${(count / max) * 80}px`,
              minHeight: count > 0 ? 4 : 0,
              background: "var(--series-1)",
              borderRadius: "4px 4px 0 0",
            }}
          />
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{bucket}</div>
        </div>
      ))}
    </div>
  );
}
