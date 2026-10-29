import { isDemoMode } from "../demo/demoMode";
import type { CheckApi } from "./checkApi";
import { httpCheckApi } from "./checkApi";

/**
 * Возвращает реализацию API. Демо-модуль загружается динамически, поэтому в
 * production-сборке он не попадает в основной бандл и недоступен по флагу.
 */
export async function loadCheckApi(): Promise<CheckApi> {
  if (isDemoMode()) {
    const { createDemoCheckApi } = await import("../demo/demoCheckApi");
    return createDemoCheckApi();
  }
  return httpCheckApi;
}
