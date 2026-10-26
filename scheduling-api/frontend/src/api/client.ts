let token: string | null = null;
let expired = () => {};
export function setToken(value: string | null) {
  token = value;
}
export function onExpired(callback: () => void) {
  expired = callback;
  return () => {
    expired = () => {};
  };
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
    public fields: Record<string, string> = {},
    public retryAfter: number | null = null,
  ) {
    super(message);
  }
}
const messages: Record<number, string> = {
  401: "Sua sessão expirou. Entre novamente.",
  403: "Você não tem permissão para esta ação.",
  404: "Registro não encontrado ou indisponível para este usuário.",
  409: "Conflito de horário ou estado. Atualize os dados e tente novamente.",
  422: "Confira os dados informados.",
  429: "Limite de tentativas excedido.",
};
export async function api<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (authenticated && token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || "/api"}${path}`,
      { ...options, headers },
    );
  } catch {
    throw new ApiError(
      "Não foi possível conectar. Verifique sua conexão e tente novamente.",
    );
  }
  const body = await response.text();
  let data: unknown;
  try {
    data = body ? JSON.parse(body) : undefined;
  } catch {
    data = undefined;
  }
  if (!response.ok) {
    const detail = (data as { detail?: unknown } | undefined)?.detail;
    const fields: Record<string, string> = {};
    if (Array.isArray(detail))
      for (const error of detail) {
        const field = error.loc?.at(-1);
        if (field)
          fields[field] =
            (
              {
                email: "Informe um e-mail válido.",
                password: "Confira o tamanho da senha.",
                name: "Informe um nome de até 120 caracteres.",
                description: "Use até 4.000 caracteres.",
                starts_at: "Informe uma data e hora válidas.",
                ends_at: "Informe uma data e hora válidas.",
              } as Record<string, string>
            )[field] || "Valor inválido.";
      }
    if (response.status === 401 && authenticated) {
      setToken(null);
      expired();
    }
    const retry = response.headers.get("Retry-After");
    const seconds = retry
      ? /^\d+$/.test(retry)
        ? Number(retry)
        : Math.max(0, Math.ceil((Date.parse(retry) - Date.now()) / 1000))
      : null;
    const message =
      response.status === 401 && !authenticated
        ? "E-mail ou senha inválidos."
        : typeof detail === "string" && [409, 422].includes(response.status)
          ? detail
          : messages[response.status] ||
            "Não foi possível concluir a operação. Tente novamente.";
    throw new ApiError(
      message + (seconds ? ` Tente novamente em ${seconds} segundos.` : ""),
      response.status,
      fields,
      seconds,
    );
  }
  return data as T;
}
export const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});
