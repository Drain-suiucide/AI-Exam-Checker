import { Header } from "./components/Header";
import { HealthStatus } from "./components/HealthStatus";

/**
 * Каркасная главная страница (T-005).
 * Только навигация, вводный блок и статус backend — без имитации проверки ответов.
 */
export default function App() {
  return (
    <div className="app">
      <Header />
      <main className="container">
        <section className="hero">
          <p className="badge">MVP / История, ЕГЭ, задание 19</p>
          <h1 className="hero-title">AI Exam Checker</h1>
          <p className="hero-text">
            Исследовательский прототип проверки развёрнутых ответов ЕГЭ по
            истории: скан&nbsp;→ OCR → оценка → объяснение → экспертная
            проверка.
          </p>
          <p className="hero-note">
            Автоматическая оценка — предварительная. Каркас находится в
            разработке: полноценная проверка ответов ещё не реализована.
          </p>
        </section>
        <HealthStatus />
      </main>
    </div>
  );
}
