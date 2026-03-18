/// <reference types="next" />

interface ImportMetaEnv {
  readonly NEXT_PUBLIC_N8N_WEBHOOK_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
