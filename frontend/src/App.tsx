import { useEffect, useState } from "react";

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
  { key: "evaluation", label: "Evaluation Center (planned)" }
];

const pagePaths: Record<PageKey, string> = {
  dashboard: "/",
  videos: "/videos",
  analysis: "/analysis",
  zones: "/zones",
  alerts: "/alerts",
  review: "/review",
  badCases: "/bad-cases",
  evaluation: "/evaluation"
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
          <p className="eyebrow">SmartTraffic</p>
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
    case "videos":
      return <VideoCenterPage onOpenAnalysisRun={openAnalysisRun} />;
    case "analysis":
      return <AnalysisDetailPage initialRunId={selectedAnalysisRunId} onOpenReview={openReviewLink} />;
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
    case "dashboard":
    default:
      return <DashboardPage onOpenAnalysisRun={openAnalysisRun} />;
  }
}

function pageFromPath(pathname: string): PageKey {
  switch (pathname) {
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
    case "/":
    default:
      return "dashboard";
  }
}
