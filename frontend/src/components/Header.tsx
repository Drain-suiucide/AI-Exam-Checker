export function Header() {
  return (
    <header className="header">
      <div className="header-inner">
        <a className="brand" href="/">
          <span className="brand-mark" aria-hidden="true" />
          AI Exam Checker
        </a>
        <nav className="header-nav" aria-label="Основная навигация">
          <a href="/">Главная</a>
          <a href="/check">Проверка</a>
          <a href="/method">Методика</a>
          <a href="/limits">Ограничения</a>
        </nav>
      </div>
    </header>
  );
}
