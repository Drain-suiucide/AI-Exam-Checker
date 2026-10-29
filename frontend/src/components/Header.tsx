import { Link, useRouter } from "../router/router";

const NAV = [
  { to: "/", label: "Главная" },
  { to: "/check", label: "Проверка" },
  { to: "/method", label: "Методика" },
  { to: "/method#limits", label: "Ограничения" },
];

export function Header() {
  const { path } = useRouter();

  return (
    <header className="header">
      <div className="header-inner">
        <Link className="brand" to="/">
          <span className="brand-mark" aria-hidden="true" />
          <span>AI Exam Checker</span>
        </Link>
        <nav className="header-nav" aria-label="Основная навигация">
          {NAV.map((item) => {
            const base = item.to.split("#")[0];
            const current = path === base && !item.to.includes("#");
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={current ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <Link className="button button-primary header-cta" to="/check">
          Проверить ответ
        </Link>
      </div>
    </header>
  );
}
