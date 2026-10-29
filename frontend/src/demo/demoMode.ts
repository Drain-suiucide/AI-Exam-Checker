/**
 * Демонстрационный режим — только для локальной разработки и только по явному
 * флагу `VITE_DEMO_MODE=true`.
 *
 * Запреты из задачи:
 * - в production-сборке демо-данные недоступны ни при каких переменных;
 * - демо-режим всегда маркируется в интерфейсе.
 */

export interface DemoEnv {
  DEV: boolean;
  PROD: boolean;
  VITE_DEMO_MODE?: string | undefined;
}

/** Чистая функция, чтобы правило можно было проверить тестом. */
export function resolveDemoMode(env: DemoEnv): boolean {
  if (env.PROD) return false;
  return env.DEV === true && env.VITE_DEMO_MODE === "true";
}

export function isDemoMode(): boolean {
  return resolveDemoMode(import.meta.env);
}
