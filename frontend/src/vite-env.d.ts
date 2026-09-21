/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Basemap style URL; defaults to OpenFreeMap positron (keyless). */
  readonly VITE_BASEMAP_STYLE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
