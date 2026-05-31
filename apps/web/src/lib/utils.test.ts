import { describe, expect, it } from "vitest";
import { formatCurrency, formatDate } from "./utils";

describe("formatCurrency", () => {
  it("formats USD with two decimals", () => {
    expect(formatCurrency(1234.567)).toBe("$1,234.57");
  });

  it("accepts strings", () => {
    expect(formatCurrency("9999.50")).toBe("$9,999.50");
  });

  it("returns em-dash for null", () => {
    expect(formatCurrency(null)).toBe("—");
    expect(formatCurrency(undefined)).toBe("—");
  });

  it("handles negative amounts", () => {
    expect(formatCurrency(-42.0)).toBe("-$42.00");
  });

  it("respects currency override", () => {
    expect(formatCurrency(100, "EUR")).toContain("€");
  });
});

describe("formatDate", () => {
  it("formats ISO dates as Mon DD, YYYY", () => {
    expect(formatDate("2026-04-15")).toMatch(/Apr 1[45], 2026/);
  });
  it("returns em-dash for null", () => {
    expect(formatDate(null)).toBe("—");
  });
});
