import { useState } from "react";

import AlertCenterPage from "./pages/AlertCenterPage";
import AnalysisDetailPage from "./pages/AnalysisDetailPage";
import BadCaseCenterPage from "./pages/BadCaseCenterPage";
import DashboardPage from "./pages/DashboardPage";
import EvaluationCenterPage from "./pages/EvaluationCenterPage";
import ReviewCenterPage from "./pages/ReviewCenterPage";
import VideoCenterPage from "./pages/VideoCenterPage";
import ZoneRuleConfigPage from "./pages/ZoneRuleConfigPage";

type PageKey =
  | "dashboard"
  | "videos"
  | "analysis"
  | "zones"
  | "alerts"
  | "review"
  | "badCases"
  | "evaluation";

const pages: Array<{ key: PageKey; label: string }> = [
  { key: "dashboard", label: "Dashboard" },
  { key: "videos", label: "Video Center" },
  { key: "analysis", label: "Analysis Detail" },
  { key: "zones", label: "Zone & Rules" },
  { key: "alerts", label: "Alert Center" },
  { key: "review", label: "Review Center" },
  { key: "badCases", label: "Bad Case Center" },
  { key: "evaluation", label: "Evaluation Center" }
];

export default function App() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">SmartTraffic</p>
          <h1>智慧交通事件检测系统</h1>
        </div>
        <nav aria-label="Main navigation">
          {pages.map((page) => (
            <button
              key={page.key}
              className={activePage === page.key ? "active" : ""}
              type="button"
              onClick={() => setActivePage(page.key)}
            >
              {page.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="workspace">{renderPage(activePage)}</main>
    </div>
  );
}

function renderPage(page: PageKey) {
  switch (page) {
    case "videos":
      return <VideoCenterPage />;
    case "analysis":
      return <AnalysisDetailPage />;
    case "zones":
      return <ZoneRuleConfigPage />;
    case "alerts":
      return <AlertCenterPage />;
    case "review":
      return <ReviewCenterPage />;
    case "badCases":
      return <BadCaseCenterPage />;
    case "evaluation":
      return <EvaluationCenterPage />;
    case "dashboard":
    default:
      return <DashboardPage />;
  }
}
