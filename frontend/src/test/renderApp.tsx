import { render } from "@testing-library/react";
import type { RenderResult } from "@testing-library/react";
import App from "../App";

/** Рендерит приложение на заданном пути (history-роутер). */
export function renderApp(path = "/"): RenderResult {
  window.history.replaceState(null, "", path);
  return render(<App />);
}

/** Эмулирует media query для проверки адаптивной разметки. */
export function mockMediaQuery(matches: boolean): void {
  window.matchMedia = ((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
