interface MetricCardsProps {
  metrics: Array<{
    label: string;
    value: string;
    detail: string;
  }>;
}

export default function MetricCards({ metrics }: MetricCardsProps) {
  return (
    <div className="metric-row">
      {metrics.map((metric) => (
        <div className="card" key={metric.label}>
          <span className="metric-value">{metric.value}</span>
          <strong>{metric.label}</strong>
          <p className="muted">{metric.detail}</p>
        </div>
      ))}
    </div>
  );
}
