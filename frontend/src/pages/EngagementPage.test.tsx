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
});
