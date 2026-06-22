import EventTable from "../components/EventTable";

export default function ReviewCenterPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h2>Review Center</h2>
          <p>事件复核队列</p>
        </div>
      </header>
      <EventTable />
    </>
  );
}
