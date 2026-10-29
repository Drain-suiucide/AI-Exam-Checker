import { Alert } from "./components/Alert";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { SkipLink } from "./components/SkipLink";
import { isDemoMode } from "./demo/demoMode";
import { CheckPage } from "./pages/CheckPage";
import { HomePage } from "./pages/HomePage";
import { MethodPage } from "./pages/MethodPage";
import { RouterProvider, useRouter, Link } from "./router/router";

function DemoBanner() {
  if (!isDemoMode()) return null;
  return (
    <div className="demo-banner" role="status">
      <Alert tone="warning" title="Демонстрационный режим">
        <p>
          Backend не используется, все данные синтетические и созданы для
          демонстрации интерфейса. Это не результат реальной проверки.
        </p>
      </Alert>
    </div>
  );
}

function NotFoundPage() {
  return (
    <section className="card" aria-labelledby="notfound-title">
      <h1 className="page-title" id="notfound-title">
        Страница не найдена
      </h1>
      <p className="card-text">Такого раздела нет. Вернитесь на главную.</p>
      <Link className="button button-primary" to="/">
        На главную
      </Link>
    </section>
  );
}

function Routes() {
  const { path } = useRouter();

  switch (path) {
    case "/":
      return <HomePage />;
    case "/check":
      return <CheckPage />;
    case "/method":
    case "/limits":
      return <MethodPage />;
    default:
      return <NotFoundPage />;
  }
}

export default function App() {
  return (
    <RouterProvider>
      <SkipLink />
      <Header />
      <DemoBanner />
      <main className="container main" id="main-content">
        <Routes />
      </main>
      <Footer />
    </RouterProvider>
  );
}
