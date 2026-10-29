import { useEffect, useState } from "react";

interface ObjectUrlState {
  status: "loading" | "ready" | "error";
  url: string | null;
}

/**
 * Скачивает blob и создаёт object URL. Нужно для страниц скана: `<img src>`
 * не умеет передавать X-Submission-Token (API_CONTRACT §1.1).
 */
export function useObjectUrl(
  load: ((signal: AbortSignal) => Promise<Blob>) | null,
): ObjectUrlState {
  const [state, setState] = useState<ObjectUrlState>({ status: "loading", url: null });

  useEffect(() => {
    if (!load) {
      setState({ status: "error", url: null });
      return;
    }
    const controller = new AbortController();
    let created: string | null = null;
    setState({ status: "loading", url: null });

    load(controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;
        created = URL.createObjectURL(blob);
        setState({ status: "ready", url: created });
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setState({ status: "error", url: null });
      });

    return () => {
      controller.abort();
      if (created) URL.revokeObjectURL(created);
    };
  }, [load]);

  return state;
}
