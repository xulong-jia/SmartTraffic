import AlertPanel from "../components/AlertPanel";

export default function AlertCenterPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h2>Alert Center</h2>
          <p>事件告警状态</p>
        </div>
      </header>
      <AlertPanel />
    </>
  );
}
