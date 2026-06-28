import ZoneEditor from "../components/ZoneEditor";

export default function ZoneRuleConfigPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h2>区域与规则</h2>
          <p>配置车道、禁停区、危险区、计数线和事件规则。</p>
        </div>
      </header>
      <section className="info-callout">
        先绘制多边形区域，按需添加方向线或计数线，填写区域信息并保存，然后创建事件规则。
      </section>
      <ZoneEditor />
    </>
  );
}
