import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Главная страница", () => {
  it("показывает заголовок, пояснение об ограничениях и оба CTA", () => {
    renderApp("/");
    expect(
      screen.getByRole("heading", {
        name: "Проверка развёрнутого ответа по истории — быстро и объяснимо",
        level: 1,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/результат — предварительный, не заменяет экспертную проверку/i)).toBeInTheDocument();
    const checkLinks = screen.getAllByRole("link", { name: "Проверить ответ" });
    expect(checkLinks.length).toBeGreaterThan(0);
    for (const link of checkLinks) {
      expect(link).toHaveAttribute("href", "/check");
    }
    expect(screen.getByRole("link", { name: "Узнать методику" })).toHaveAttribute("href", "/method");
  });

  it("использует существующие изображения с текстовым описанием", () => {
    renderApp("/");
    const images = screen.getAllByRole("img");
    expect(images.length).toBeGreaterThanOrEqual(2);
    for (const image of images) {
      expect(image.getAttribute("src")).toMatch(/^\/images\/.+\.svg$/);
      expect(image.getAttribute("alt")).toBeTruthy();
    }
  });

  it("содержит доступную навигацию с текущим разделом", () => {
    renderApp("/");
    const nav = screen.getByRole("navigation", { name: "Основная навигация" });
    expect(within(nav).getByRole("link", { name: "Главная" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Методика" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Перейти к основному содержанию" })).toHaveAttribute(
      "href",
      "#main-content",
    );
  });

  it("переходит на страницу проверки по CTA без перезагрузки", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getAllByRole("link", { name: "Проверить ответ" })[0]);
    expect(window.location.pathname).toBe("/check");
    expect(screen.getByRole("heading", { name: "Проверка развёрнутого ответа", level: 1 })).toBeInTheDocument();
  });
});

describe("Страница методики", () => {
  it("явно описывает ограничения и отсутствие официального балла", () => {
    renderApp("/method");
    expect(screen.getByRole("heading", { name: "Методика и ограничения прототипа" })).toBeInTheDocument();
    expect(screen.getByText(/Система не выставляет официальные баллы ЕГЭ/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ограничения и данные" })).toBeInTheDocument();
  });
});

describe("Неизвестный маршрут", () => {
  it("показывает страницу 404", () => {
    renderApp("/unknown");
    expect(screen.getByRole("heading", { name: "Страница не найдена" })).toBeInTheDocument();
  });
});
