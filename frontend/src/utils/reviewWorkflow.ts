import type {
  BadCaseFromReviewRequest,
  ReviewActionRequest,
  ReviewActionResponse,
  ReviewComment,
  ReviewEventDetail
} from "../types";

export type ReviewWorkflowAction =
  | "confirm"
  | "false-positive"
  | "ignore"
  | "resolve"
  | "comment"
  | "bad-case"
  | "rerun-rule";

export interface ReviewWorkflowFormState {
  runId: string;
  eventId: string | null;
  reviewer: string;
  comment: string;
  alertId?: string | null;
}

export interface ReviewWorkflowValidation {
  valid: boolean;
  message: string;
}

export interface ReviewWorkflowActionItem {
  action: ReviewWorkflowAction;
  label: string;
  description: string;
  requiresComment: boolean;
}

export const REVIEW_WORKFLOW_ACTIONS: ReviewWorkflowActionItem[] = [
  {
    action: "confirm",
    label: "Confirm",
    description: "Confirm the event as a valid detection.",
    requiresComment: false
  },
  {
    action: "false-positive",
    label: "False positive",
    description: "Mark the event as incorrectly triggered.",
    requiresComment: true
  },
  {
    action: "ignore",
    label: "Ignore",
    description: "Leave the event out of current review decisions.",
    requiresComment: false
  },
  {
    action: "resolve",
    label: "Resolve",
    description: "Close a reviewed event after follow-up.",
    requiresComment: false
  },
  {
    action: "comment",
    label: "Comment",
    description: "Append an audit comment without changing status.",
    requiresComment: true
  },
  {
    action: "bad-case",
    label: "Create Bad Case",
    description: "Create a review-linked Bad Case for later regression.",
    requiresComment: false
  },
  {
    action: "rerun-rule",
    label: "Request rule rerun",
    description: "Record a rule_rerun processing task request.",
    requiresComment: true
  }
];

export function validateReviewWorkflowAction(
  action: ReviewWorkflowAction,
  form: ReviewWorkflowFormState
): ReviewWorkflowValidation {
  if (!form.runId.trim()) {
    return { valid: false, message: "run_id is required." };
  }
  if (!form.eventId?.trim()) {
    return { valid: false, message: "Select an event first." };
  }
  if (requiresComment(action) && !form.comment.trim()) {
    return { valid: false, message: "Comment is required for this action." };
  }
  return { valid: true, message: "" };
}

export function buildReviewActionRequest(
  form: ReviewWorkflowFormState
): ReviewActionRequest {
  return {
    run_id: form.runId.trim(),
    comment: form.comment.trim(),
    reviewer: normalizeReviewer(form.reviewer),
    alert_id: form.alertId ?? null
  };
}

export function buildReviewCommentRequest(form: ReviewWorkflowFormState) {
  return {
    run_id: form.runId.trim(),
    event_id: form.eventId?.trim() ?? "",
    comment: form.comment.trim(),
    reviewer: normalizeReviewer(form.reviewer),
    alert_id: form.alertId ?? null
  };
}

export function buildBadCaseFromReviewRequest(
  detail: ReviewEventDetail,
  form: ReviewWorkflowFormState
): BadCaseFromReviewRequest {
  const latestReview = selectLatestReviewComment(detail.comments);
  const event = detail.event;
  return {
    run_id: form.runId.trim() || detail.run_id,
    event_id: form.eventId?.trim() || event.event_id,
    review_id: latestReview?.review_id ?? null,
    case_type: inferBadCaseTypeFromReview(latestReview?.action, event.review_status),
    module: "review_center",
    description: form.comment.trim() || latestReview?.comment || `Review follow-up for ${event.event_id}`,
    expected_result: expectedResultForReview(latestReview?.action, event.review_status),
    actual_result: actualResultForReview(event.event_type, event.original_status),
    root_cause: "Pending manual triage from Review Center.",
    tags: ["review_center", "needs_regression"]
  };
}

export function buildReviewSuccessMessage(
  action: ReviewWorkflowAction,
  response?: unknown
): string {
  if (action === "bad-case") {
    const caseId = readString(response, "case_id");
    return caseId ? `Bad Case created: ${caseId}.` : "Bad Case created.";
  }
  if (action === "rerun-rule") {
    const taskId = readString(response, "task_id") || readString(response, "processing_task_id");
    return taskId ? `Rule rerun requested: ${taskId}.` : "Rule rerun requested.";
  }
  if (action === "comment") {
    return "Comment added.";
  }
  return `Review action saved: ${actionLabel(action)}.`;
}

export function selectLatestReviewComment(
  comments: ReviewComment[]
): ReviewComment | null {
  if (comments.length === 0) {
    return null;
  }
  return comments.reduce((latest, current) => {
    const latestTime = Date.parse(latest.created_at);
    const currentTime = Date.parse(current.created_at);
    if (Number.isNaN(latestTime) || Number.isNaN(currentTime)) {
      return current;
    }
    return currentTime >= latestTime ? current : latest;
  });
}

export function actionLabel(action: ReviewWorkflowAction): string {
  return REVIEW_WORKFLOW_ACTIONS.find((item) => item.action === action)?.label ?? action;
}

function requiresComment(action: ReviewWorkflowAction): boolean {
  return REVIEW_WORKFLOW_ACTIONS.some(
    (item) => item.action === action && item.requiresComment
  );
}

function normalizeReviewer(value: string): string {
  return value.trim() || "local_reviewer";
}

function inferBadCaseTypeFromReview(
  action: string | null | undefined,
  status: string | null | undefined
): string {
  if (action === "mark_false_positive" || status === "false_positive") {
    return "false_positive";
  }
  if (action === "add_false_negative" || status === "false_negative") {
    return "false_negative";
  }
  return "event_rule_error";
}

function expectedResultForReview(
  action: string | null | undefined,
  status: string | null | undefined
): string {
  if (action === "mark_false_positive" || status === "false_positive") {
    return "Event rule should not emit this event.";
  }
  if (action === "add_false_negative" || status === "false_negative") {
    return "Event rule should emit the expected event.";
  }
  return "Event review state should match reviewer decision.";
}

function actualResultForReview(
  eventType: string | null | undefined,
  originalStatus: string | null | undefined
): string {
  const eventLabel = eventType?.trim() || "event";
  const statusLabel = originalStatus?.trim() || "unknown";
  return `${eventLabel} was produced with original status ${statusLabel}.`;
}

function readString(
  response: unknown,
  key: string
): string | null {
  if (!response || typeof response !== "object") {
    return null;
  }
  const value = (response as Record<string, unknown>)[key];
  return typeof value === "string" ? value : null;
}
