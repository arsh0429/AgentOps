import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import DriftHome from "./DriftHome";

beforeEach(() => vi.restoreAllMocks());

function renderHome() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><DriftHome /></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DriftHome", () => {
  it("shows three drift signal cards labeled correctly", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      const u = String(url);
      if (u.includes("/drift")) return new Response(JSON.stringify({ signals: [] }), { status: 200 });
      if (u.includes("/runs")) return new Response(JSON.stringify({ runs: [] }), { status: 200 });
      return new Response("not found", { status: 404 });
    });
    renderHome();
    await waitFor(() => expect(screen.queryByText("Lexical input drift")).not.toBeNull());
    expect(screen.queryByText("Tool-call drift")).not.toBeNull();
    expect(screen.queryByText("Quality drift")).not.toBeNull();
  });
});
