interface AppEnv {
  apiUrl: string;
}

function readEnv(): AppEnv {
  const apiUrl = import.meta.env.VITE_API_URL ?? '/api';

  if (typeof apiUrl !== 'string' || apiUrl.trim().length === 0) {
    throw new Error('VITE_API_URL must be a non-empty string or omitted to use /api');
  }

  return { apiUrl: apiUrl.replace(/\/$/, '') };
}

export const env = readEnv();
