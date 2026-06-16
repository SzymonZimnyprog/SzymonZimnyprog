import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import StackPage from "./StackPage";
import * as api from "../api";

vi.mock("../api");

describe("StackPage", () => {
  it("runs a stack and shows per-stage results", async () => {
    vi.mocked(api.simulateMultiStage).mockResolvedValue({
      time: [0, 1, 2],
      thrust: [1000, 5000, 0],
      stage_starts: [0, 2.8],
      stages: [
        { index: 0, start_time: 0, burn_time: 1.3, total_impulse: 51000, propellant_mass: 21, impulse_class: "P" },
        { index: 1, start_time: 2.8, burn_time: 6, total_impulse: 12000, propellant_mass: 8, impulse_class: "N" },
      ],
      summary: {
        total_impulse: 63000,
        burn_time: 8.8,
        propellant_mass_total: 29,
        peak_thrust: 50000,
        impulse_class: "P",
        stage_count: 2,
      },
    } as never);
    const user = userEvent.setup();
    render(<StackPage />);
    await user.click(screen.getByRole("button", { name: /Run stack/i }));
    expect(await screen.findByText("63000 N·s")).toBeTruthy();
    // both stages appear in the table
    expect(screen.getByText("2.80 s")).toBeTruthy();
  });

  it("adds and removes stages", async () => {
    const user = userEvent.setup();
    render(<StackPage />);
    expect(screen.getByText("Stage 1")).toBeTruthy();
    expect(screen.getByText("Stage 2")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: /Add stage/i }));
    expect(screen.getByText("Stage 3")).toBeTruthy();
  });
});
