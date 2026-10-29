/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Включает демо-данные только в dev-сборке (см. src/demo/demoMode.ts). */
  readonly VITE_DEMO_MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
