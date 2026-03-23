import type { TemplateApi } from "../electron/preload";

declare global {
  interface Window {
    templateApi?: TemplateApi;
  }
}

export {};
