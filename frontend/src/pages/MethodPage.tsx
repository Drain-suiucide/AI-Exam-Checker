import { Alert } from "../components/Alert";
import { Link } from "../router/router";

export function MethodPage() {
  return (
    <article className="prose-page" aria-labelledby="method-title">
      <h1 className="page-title" id="method-title" tabIndex={-1}>
        Методика и ограничения прототипа
      </h1>

      <section className="card" aria-labelledby="method-checked">
        <h2 className="card-title" id="method-checked">
          Что проверяется
        </h2>
        <p className="card-text">
          Развёрнутый ответ по истории: и фактическое знание, и точность
          формулировки. Оценивание выполняется только по подтверждённой
          конфигурации — фиксированному набору версий экзамена, задания,
          критериев и профиля оценивания.
        </p>
        <ul className="prose-list">
          <li>Ответ распознаётся из изображения или принимается как текст.</li>
          <li>Текст можно исправить до запуска проверки.</li>
          <li>
            По каждому критерию выводятся балл, обоснование и фрагменты ответа.
          </li>
        </ul>
      </section>

      <section className="card" aria-labelledby="method-not-checked">
        <h2 className="card-title" id="method-not-checked">
          Что не проверяется
        </h2>
        <ul className="prose-list">
          <li>Система не выставляет официальные баллы ЕГЭ.</li>
          <li>В MVP один предмет (история) и одна задача.</li>
          <li>Не выполняется проверка всей экзаменационной работы.</li>
          <li>Нет личных кабинетов и платёжных функций.</li>
        </ul>
      </section>

      <section className="card" aria-labelledby="method-confidence">
        <h2 className="card-title" id="method-confidence">
          Как оценивается уверенность
        </h2>
        <p className="card-text">
          Значение «уверенность» — это самооценка модели от 0 до 1. Это не
          вероятность правильности ответа и не гарантия результата. Низкая
          уверенность по критерию или флагам отображается отдельной пометкой.
        </p>
      </section>

      <section className="card" aria-labelledby="method-review">
        <h2 className="card-title" id="method-review">
          Когда требуется эксперт
        </h2>
        <p className="card-text">
          Если модель отмечает низкую уверенность, спорные фрагменты или
          невозможность найти подтверждение, результат помечается как требующий
          экспертной проверки. Пользователь может отправить запрос на проверку с
          указанием причины.
        </p>
        <Alert tone="warning" title="Автоматическая оценка — предварительная">
          <p>
            Она не заменяет экспертное решение. Статус «требуется проверка»
            означает, что нужно проверить логику и формулу оценки, а не что
            ответ неверный.
          </p>
        </Alert>
      </section>

      <section className="card" id="limits" aria-labelledby="method-limits">
        <h2 className="card-title" id="method-limits">
          Ограничения и данные
        </h2>
        <ul className="prose-list">
          <li>В прототипе не используются реальные данные учащихся.</li>
          <li>
            Для тестов применяются синтетические или обезличенные примеры —
            пользователь подтверждает это при загрузке.
          </li>
          <li>
            Ответы не сохраняются в браузере: при обновлении страницы доступ к
            текущей отправке теряется.
          </li>
          <li>
            Отправку можно удалить в любой момент, когда не идёт обработка.
          </li>
          <li>
            Допустимы изображения JPG, PNG, WebP; PDF и HEIC в MVP не
            поддерживаются.
          </li>
        </ul>
      </section>

      <p className="page-actions">
        <Link className="button button-primary" to="/check">
          Проверить ответ
        </Link>
        <Link className="button button-secondary" to="/">
          На главную
        </Link>
      </p>
    </article>
  );
}
