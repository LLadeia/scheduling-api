export const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
export const formatDate = (value: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
export function toLocalInput(value: string) {
  const date = new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
export function toUTC(value: string) {
  return new Date(value).toISOString();
}
export function intervalErrors(
  start: string,
  end: string,
  future = true,
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!start || !Number.isFinite(+new Date(start)))
    errors.starts_at = "Informe um início válido.";
  else if (future && +new Date(start) <= Date.now())
    errors.starts_at = "O início deve estar no futuro.";
  if (!end || !Number.isFinite(+new Date(end)))
    errors.ends_at = "Informe um fim válido.";
  else if (start && +new Date(end) <= +new Date(start))
    errors.ends_at = "O fim deve ser posterior ao início.";
  return errors;
}
