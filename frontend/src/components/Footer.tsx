import { Link } from "../router/router";

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <p>
          Исследовательский MVP. Автоматическая оценка предварительная и не
          заменяет экспертную проверку.
        </p>
        <p>
          <Link to="/method">Методика и ограничения</Link>
        </p>
      </div>
    </footer>
  );
}
