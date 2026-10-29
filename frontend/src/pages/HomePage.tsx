import { Link } from "../router/router";
import { StatusBadge } from "../components/StatusBadge";

const WORKFLOW = [
  { title: "Загрузка", text: "Скан ответа или текст, введённый вручную." },
  { title: "Распознавание", text: "OCR (распознавание текста) с возможностью исправить." },
  { title: "Проверка", text: "Оценка по подтверждённым критериям конфигурации." },
  { title: "Объяснение", text: "Фрагменты ответа и обоснование по каждому критерию." },
];

export function HomePage() {
  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <p className="badge">Исследовательский MVP · История · ЕГЭ</p>
          <h1 className="hero-title" id="hero-title">
            Проверка развёрнутого ответа по истории — быстро и объяснимо
          </h1>
          <p className="hero-text">
            AI Exam Checker помогает показать, как автоматически распознаётся
            ответ, проверяется по критериям и формируется предварительная
            оценка.
          </p>
          <p className="hero-note">
            Прототип предназначен для исследования и демонстрации подхода;
            результат — предварительный, не заменяет экспертную проверку.
          </p>
          <div className="hero-actions">
            <Link className="button button-primary button-large" to="/check">
              Проверить ответ
            </Link>
            <Link className="button button-secondary button-large" to="/method">
              Узнать методику
            </Link>
          </div>
        </div>
        <div className="hero-visual">
          <img
            src="/images/hero-illustration.svg"
            alt="Иллюстрация: скан ответа преобразуется в текст и проверяется по критериям"
            width={780}
            height={560}
            loading="eager"
          />
        </div>
      </section>

      <section className="feature-grid" aria-labelledby="features-title">
        <h2 className="section-title" id="features-title">
          Что показывает прототип
        </h2>
        <ul className="feature-list">
          <li className="card feature-card">
            <StatusBadge tone="info">OCR</StatusBadge>
            <h3 className="feature-title">Распознавание с правкой</h3>
            <p className="card-text">
              Текст распознаётся автоматически, а пользователь может исправить
              ошибки до оценки.
            </p>
          </li>
          <li className="card feature-card">
            <StatusBadge tone="info">Критерии</StatusBadge>
            <h3 className="feature-title">Баллы по каждому критерию</h3>
            <p className="card-text">
              Оценивание идёт только по утверждённой конфигурации экзамена,
              задания и критериев.
            </p>
          </li>
          <li className="card feature-card">
            <StatusBadge tone="warning">Проверка эксперта</StatusBadge>
            <h3 className="feature-title">Прозрачные ограничения</h3>
            <p className="card-text">
              Если модель не уверена, интерфейс прямо просит экспертную
              проверку и не скрывает статус.
            </p>
          </li>
        </ul>
      </section>

      <section className="workflow" aria-labelledby="workflow-title">
        <div className="workflow-copy">
          <h2 className="section-title" id="workflow-title">
            Как проходит проверка
          </h2>
          <ol className="workflow-list">
            {WORKFLOW.map((step, index) => (
              <li key={step.title}>
                <span className="workflow-number" aria-hidden="true">
                  {index + 1}
                </span>
                <div>
                  <h3 className="workflow-title">{step.title}</h3>
                  <p className="workflow-text">{step.text}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="hero-note">
            В MVP доступны только подтверждённые конфигурации проверки. Иные
            предметы и задания временно недоступны.
          </p>
        </div>
        <div className="workflow-visual">
          <img
            src="/images/scan-workflow.svg"
            alt="Схема: загрузка ответа, распознавание, проверка по критериям и обоснование"
            width={960}
            height={520}
            loading="lazy"
          />
        </div>
      </section>
    </>
  );
}
