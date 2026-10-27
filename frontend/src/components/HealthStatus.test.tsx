import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { HealthStatus } from "./HealthStatus";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HealthStatus", () => {
  it("показывает статус «Backend доступен» при успешном ответе", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: "ok",
            service: "ai-exam-checker-backend",
            version: "0.1.0",
          }),
          { status: 200 },
        ),
      ),
    );

    render(<HealthStatus />);
    await waitFor(() =>
      expect(screen.getByText("Backend доступен")).toBeInTheDocument(),
    );
    expect(screen.getByText(/ai-exam-checker-backend/)).toBeInTheDocument();
  });

  it("показывает состояние ошибки, если backend недоступен", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Ошибка сети")));

    render(<HealthStatus />);
    await waitFor(() =>
      expect(screen.getByText("Backend недоступен")).toBeInTheDocument(),
    );
    expect(screen.getByText(/Ошибка сети/)).toBeInTheDocument();
  });
});
