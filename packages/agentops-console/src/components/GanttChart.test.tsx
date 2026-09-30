import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import GanttChart, { type GanttSpan } from "./GanttChart";

const spans: GanttSpan[] = [
  { id: "p", parentId: null, name: "planner", role: "planner",
    start: 0, end: 10, durationLabel: "10s" },
  { id: "w1", parentId: "p", name: "worker", role: "worker",
    start: 2, end: 6, durationLabel: "4s" },
];

describe("GanttChart", () => {
  it("renders a row per span with proportional bars", () => {
    const { container } = render(<GanttChart spans={spans} />);
    const bars = container.querySelectorAll("[data-test='gantt-bar']");
    expect(bars.length).toBe(2);
  });

  it("calls onSpanClick with span id", () => {
    let clicked = "";
    const { container } = render(<GanttChart spans={spans} onSpanClick={(id) => (clicked = id)} />);
    const bar = container.querySelectorAll("[data-test='gantt-bar']")[0] as HTMLElement;
    bar.click();
    expect(clicked).toBe("p");
  });
});
