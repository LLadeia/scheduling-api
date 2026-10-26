import { Field } from "./UI";
import { timezone } from "../utils/dates";
export default function TimeFields({
  start,
  end,
  setStart,
  setEnd,
  errors = {},
}: {
  start: string;
  end: string;
  setStart: (s: string) => void;
  setEnd: (s: string) => void;
  errors?: Record<string, string>;
}) {
  return (
    <>
      <div className="form-grid">
        <Field
          label="Início"
          type="datetime-local"
          required
          value={start}
          onChange={(e) => setStart(e.target.value)}
          error={errors.starts_at}
        />
        <Field
          label="Fim"
          type="datetime-local"
          required
          value={end}
          onChange={(e) => setEnd(e.target.value)}
          error={errors.ends_at}
        />
      </div>
      <p className="hint">Horários no fuso {timezone}.</p>
    </>
  );
}
