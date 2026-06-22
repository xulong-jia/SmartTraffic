import ZoneEditor from "../components/ZoneEditor";

export default function ZoneRuleConfigPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h2>Zone & Rule Config</h2>
          <p>区域、方向线、计数线和规则阈值</p>
        </div>
      </header>
      <ZoneEditor />
    </>
  );
}
