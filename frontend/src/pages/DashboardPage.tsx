import MetricCards from "../components/MetricCards";

export default function DashboardPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p>阶段一数据面板</p>
        </div>
      </header>
      <MetricCards
        metrics={[
          { label: "Videos", value: "0", detail: "uploaded" },
          { label: "Runs", value: "0", detail: "created" },
          { label: "Events", value: "0", detail: "pending" },
          { label: "Alerts", value: "0", detail: "new" }
        ]}
      />
    </>
  );
}
