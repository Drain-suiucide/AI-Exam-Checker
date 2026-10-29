/**
 * Минимальный клиентский роутер на History API.
 *
 * Приложение намеренно не тянет библиотеку роутинга: маршрутов мало, а
 * nginx уже настроен на SPA-fallback (`try_files ... /index.html`).
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { AnchorHTMLAttributes, MouseEvent, ReactNode } from "react";

interface RouterValue {
  path: string;
  hash: string;
  navigate: (to: string, options?: { replace?: boolean }) => void;
}

const RouterContext = createContext<RouterValue | null>(null);

function currentLocation(): { path: string; hash: string } {
  return { path: window.location.pathname, hash: window.location.hash };
}

export function RouterProvider({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState(currentLocation);

  useEffect(() => {
    const onChange = () => setLocation(currentLocation());
    window.addEventListener("popstate", onChange);
    return () => window.removeEventListener("popstate", onChange);
  }, []);

  const navigate = useCallback((to: string, options?: { replace?: boolean }) => {
    if (options?.replace) {
      window.history.replaceState(null, "", to);
    } else {
      window.history.pushState(null, "", to);
    }
    setLocation(currentLocation());
  }, []);

  const value = useMemo(
    () => ({ ...location, navigate }),
    [location, navigate],
  );

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useRouter(): RouterValue {
  const value = useContext(RouterContext);
  if (!value) {
    throw new Error("useRouter должен вызываться внутри RouterProvider");
  }
  return value;
}

interface LinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  to: string;
  children: ReactNode;
}

/** Ссылка с клиентской навигацией; Cmd/Ctrl/Shift-клик работает как обычная. */
export function Link({ to, onClick, children, ...rest }: LinkProps) {
  const { navigate } = useRouter();

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event);
    if (event.defaultPrevented) return;
    if (event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  };

  return (
    <a href={to} onClick={handleClick} {...rest}>
      {children}
    </a>
  );
}
