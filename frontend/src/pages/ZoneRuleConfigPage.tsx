import ZoneEditor from "../components/ZoneEditor";

export default function ZoneRuleConfigPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h2>区域与规则 Zone & Rules</h2>
          <p>配置车道、禁停区、危险区、计数线和事件规则。</p>
        </div>
      </header>
      <ZoneEditor />
    </>
  );
}
