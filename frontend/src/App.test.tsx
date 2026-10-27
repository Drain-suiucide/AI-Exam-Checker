import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App (каркасная страница)", () => {
  it("показывает заголовок и бейдж этапа MVP", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "AI Exam Checker" })).toBeInTheDocument();
    expect(screen.getByText(/MVP \/ История, ЕГЭ, задание 19/)).toBeInTheDocument();
  });

  it("содержит навигацию из дизайн-системы", () => {
    render(<App />);
    const nav = screen.getByRole("navigation", { name: "Основная навигация" });
    expect(nav).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Главная" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ограничения" })).toBeInTheDocument();
  });
});
