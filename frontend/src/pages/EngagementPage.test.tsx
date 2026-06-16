import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EngagementPage from "./EngagementPage";
import * as api from "../api";

vi.mock("../api");

const result = {
  time: [0, 1, 2],
  interceptor_position: [[0, 0, 0], [100, 0, 100], [200, 0, 150]],
  target_position: [[1500, 0, 800], [1200, 0, 770], [200, 0, 150]],
  separation: [1700, 1100, 4],
  interceptor_speed: [40, 300, 800],
  target_speed: [300, 300, 300],
  interceptor_accel_cmd: [0, 50, 120],
  summary: {
    intercepted: true,
    miss_distance: 4,
    intercept_time: 2,
    intercept_point: [200, 0, 150],
    closing_speed_at_intercept: 900,
  },
  interceptor_motor_summary: {
    burn_time: 1.5,
    total_impulse: 90000,
    specific_impulse: 220,
    peak_thrust: 60000,
    average_thrust: 50000,
    peak_pressure: 7e6,
    propellant_mass_initial: 40,
    impulse_class: "Q",
  },
};

describe("EngagementPage", () => {
  it("shows the intercept verdict after running", async () => {
    vi.mocked(api.simulateEngagement).mockResolvedValue(result as never);
    const user = userEvent.setup();
    render(<EngagementPage />);
    await user.click(screen.getByRole("button", { name: /Run engagement/i }));
    expect(await screen.findByText(/miss 4.0 m/i)).toBeTruthy();
    expect(screen.getByText("✓ INTERCEPT")).toBeTruthy();
  });

  it("shows the firing solution after auto-aim", async () => {
    vi.mocked(api.solveEngagement).mockResolvedValue({
      intercepted: true,
      elevation_deg: 25.2,
      azimuth_deg: 90,
      miss_distance: 0.3,
      intercept_time: 23.6,
      intercept_point: [10000, 0, 6000],
      envelope: [
        { elevation: 10, miss: 4000, hit: false },
        { elevation: 25, miss: 0.3, hit: true },
        { elevation: 80, miss: 5000, hit: false },
      ],
      engagement: result,
      interceptor_motor_summary: result.interceptor_motor_summary,
    } as never);
    const user = userEvent.setup();
    render(<EngagementPage />);
    await user.click(screen.getByRole("button", { name: /Auto-aim/i }));
    expect(await screen.findByText(/elevation 25.2°/i)).toBeTruthy();
    expect(screen.getByText("Firing solution")).toBeTruthy();
  });

  it("shows salvo results after firing", async () => {
    vi.mocked(api.salvoEngagement).mockResolvedValue({
      count: 3,
      hits: 2,
      intercepted: true,
      best_miss: 1.2,
      azimuth_deg: 90,
      success_fraction: 2 / 3,
      shots: [
        { index: 0, launch_time: 0, elevation_deg: 42, intercepted: false, miss_distance: 7, intercept_time: 18 },
        { index: 1, launch_time: 1.5, elevation_deg: 45, intercepted: true, miss_distance: 1.2, intercept_time: 19 },
        { index: 2, launch_time: 3, elevation_deg: 48, intercepted: true, miss_distance: 3, intercept_time: 20 },
      ],
      interceptor_motor_summary: result.interceptor_motor_summary,
    } as never);
    const user = userEvent.setup();
    render(<EngagementPage />);
    await user.click(screen.getByRole("button", { name: /Fire salvo/i }));
    expect(await screen.findByText(/TARGET NEUTRALISED/i)).toBeTruthy();
    expect(screen.getByText(/2\/3 hits/i)).toBeTruthy();
  });

  it("shows Monte-Carlo Pk after running", async () => {
    vi.mocked(api.montecarloEngagement).mockResolvedValue({
      trials: 100,
      hits: 87,
      pk: 0.87,
      elevation_deg: 49,
      azimuth_deg: 90,
      mean_miss: 3,
      median_miss: 3.1,
      p90_miss: 5.1,
      histogram_edges: [0, 1, 2, 3],
      histogram_counts: [10, 40, 37],
    } as never);
    const user = userEvent.setup();
    render(<EngagementPage />);
    await user.click(screen.getByRole("button", { name: /Run Monte-Carlo/i }));
    expect(await screen.findByText(/Pk 87%/i)).toBeTruthy();
    expect(screen.getByText(/87\/100 kills/i)).toBeTruthy();
  });
});
