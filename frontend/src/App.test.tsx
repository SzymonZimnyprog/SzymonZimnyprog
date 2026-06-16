import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import * as api from "./api";

vi.mock("./api");

const mockItems = [{ id: 1, name: "Example Item", description: "A sample item" }];

beforeEach(() => {
  vi.mocked(api.fetchItems).mockResolvedValue(mockItems);
});

describe("App", () => {
  it("renders the simulator heading", () => {
    render(<App />);
    expect(screen.getByText(/Interceptor & Solid-Motor Simulator/i)).toBeTruthy();
  });

  it("defaults to the interception tab", () => {
    render(<App />);
    expect(screen.getByText("Interception engagement")).toBeTruthy();
  });

  it("switches to the motor tab", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Motor" }));
    expect(
      screen.getByRole("heading", { name: /Solid rocket motor/i })
    ).toBeTruthy();
  });

  it("loads items on the items tab", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Items" }));
    expect(await screen.findByText("Example Item")).toBeTruthy();
  });
});
