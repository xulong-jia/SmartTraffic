import type { ReactNode } from "react";

interface CollapsibleSectionProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export default function CollapsibleSection({
  title,
  children,
  className = ""
}: CollapsibleSectionProps) {
  const classes = ["collapsible-section", className].filter(Boolean).join(" ");
  return (
    <details className={classes}>
      <summary>{title}</summary>
      <div className="collapsible-body">{children}</div>
    </details>
  );
}
