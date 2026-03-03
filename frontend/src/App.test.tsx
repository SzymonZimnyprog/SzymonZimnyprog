import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";
import * as api from "./api";

vi.mock("./api");

const mockItems = [
  { id: 1, name: "Example Item", description: "A sample item" },
];

beforeEach(() => {
  vi.mocked(api.fetchItems).mockResolvedValue(mockItems);
});

describe("App", () => {
  it("renders the heading", async () => {
    render(<App />);
    expect(screen.getByText("Items")).toBeTruthy();
  });

  it("shows items after loading", async () => {
    render(<App />);
    const item = await screen.findByText("Example Item");
    expect(item).toBeTruthy();
  });
});
