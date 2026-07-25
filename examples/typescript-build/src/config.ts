
export interface AppConfig {
  apiBaseUrl: string
  region: string
}

export function loadConfig(): AppConfig {
  return {
    apiBaseUrl: process.env.API_BASE_URL ?? 'http://127.0.0.1:3000',
    region: process.env.DEPLOY_REGION,
  }
}
