import { useEffect, useState } from "react";

import AlertCenterPage from "./pages/AlertCenterPage";
import AnalysisDetailPage from "./pages/AnalysisDetailPage";
import BadCaseCenterPage from "./pages/BadCaseCenterPage";
import CameraCenterPage from "./pages/CameraCenterPage";
import DashboardPage from "./pages/DashboardPage";
import EvaluationCenterPage from "./pages/EvaluationCenterPage";
import ReportCenterPage from "./pages/ReportCenterPage";
import ReviewCenterPage from "./pages/ReviewCenterPage";
import VideoCenterPage from "./pages/VideoCenterPage";
import ZoneRuleConfigPage from "./pages/ZoneRuleConfigPage";
import { resolveAnalysisInitialRunId } from "./utils/analysisNavigation";

type PageKey =
  | "dashboard"
  | "cameras"
  | "videos"
  | "analysis"
  | "zones"
  | "alerts"
  | "review"
  | "badCases"
  | "evaluation"
  | "reports";

const pages: Array<{ key: PageKey; label: string }> = [
  { key: "dashboard", label: "总览 Dashboard" },
  { key: "cameras", label: "摄像头中心 Camera" },
  { key: "videos", label: "视频中心 Video" },
  { key: "analysis", label: "分析详情 Analysis" },
  { key: "zones", label: "区域与规则 Zone & Rules" },
  { key: "alerts", label: "告警中心 Alert" },
  { key: "review", label: "复核中心 Review" },
  { key: "badCases", label: "坏例中心 Bad Case" },
  { key: "evaluation", label: "评测中心 Evaluation" },
  { key: "reports", label: "报告中心 Report" }
];

const pagePaths: Record<PageKey, string> = {
  dashboard: "/",
  cameras: "/cameras",
  videos: "/videos",
  analysis: "/analysis",
  zones: "/zones",
  alerts: "/alerts",
  review: "/review",
  badCases: "/bad-cases",
  evaluation: "/evaluation",
  reports: "/reports"
};

export default function App() {
  const [activePage, setActivePage] = useState<PageKey>(() =>
    pageFromPath(window.location.pathname)
  );
  const [locationSearch, setLocationSearch] = useState(window.location.search);
  const [selectedAnalysisRunId, setSelectedAnalysisRunId] = useState("");

  useEffect(() => {
    function handlePopState() {
      setActivePage(pageFromPath(window.location.pathname));
      setLocationSearch(window.location.search);
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function navigateToPage(page: PageKey) {
    const nextPath = pagePaths[page];
    if (window.location.pathname !== nextPath || window.location.search) {
      window.history.pushState(null, "", nextPath);
    }
    setActivePage(page);
    setLocationSearch("");
  }

  function openAnalysisRun(runId: string) {
    setSelectedAnalysisRunId(runId);
    window.history.pushState(null, "", `/analysis?run_id=${encodeURIComponent(runId)}`);
    setActivePage("analysis");
    setLocationSearch(window.location.search);
  }

  function openReviewLink(href: string) {
    window.history.pushState(null, "", href);
    setActivePage("review");
    setLocationSearch(window.location.search);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">SMARTTRAFFIC</p>
          <h1>智慧交通事件检测系统</h1>
        </div>
        <nav aria-label="Main navigation">
          {pages.map((page) => (
            <button
              key={page.key}
              className={activePage === page.key ? "active" : ""}
              type="button"
              onClick={() => navigateToPage(page.key)}
            >
              {page.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="workspace">
        {renderPage(activePage, selectedAnalysisRunId, openAnalysisRun, openReviewLink, locationSearch)}
      </main>
    </div>
  );
}

function renderPage(
  page: PageKey,
  selectedAnalysisRunId: string,
  openAnalysisRun: (runId: string) => void,
  openReviewLink: (href: string) => void,
  locationSearch: string
) {
  switch (page) {
    case "cameras":
      return <CameraCenterPage />;
    case "videos":
      return <VideoCenterPage onOpenAnalysisRun={openAnalysisRun} />;
    case "analysis":
      return (
        <AnalysisDetailPage
          initialRunId={resolveAnalysisInitialRunId(selectedAnalysisRunId, locationSearch)}
          onOpenReview={openReviewLink}
        />
      );
    case "zones":
      return <ZoneRuleConfigPage />;
    case "alerts":
      return <AlertCenterPage onOpenReview={openReviewLink} />;
    case "review":
      return <ReviewCenterPage locationSearch={locationSearch} />;
    case "badCases":
      return <BadCaseCenterPage />;
    case "evaluation":
      return <EvaluationCenterPage />;
    case "reports":
      return <ReportCenterPage />;
    case "dashboard":
    default:
      return <DashboardPage onOpenAnalysisRun={openAnalysisRun} />;
  }
}

function pageFromPath(pathname: string): PageKey {
  switch (pathname) {
    case "/cameras":
      return "cameras";
    case "/videos":
      return "videos";
    case "/analysis":
      return "analysis";
    case "/zones":
      return "zones";
    case "/alerts":
      return "alerts";
    case "/review":
      return "review";
    case "/bad-cases":
      return "badCases";
    case "/evaluation":
      return "evaluation";
    case "/reports":
      return "reports";
    case "/":
    default:
      return "dashboard";
  }
}
