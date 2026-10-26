import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api, json } from "../api/client";
import { Form, Message, PageTitle, useSubmit } from "../components/UI";
import TimeFields from "../components/TimeFields";
import type { Appointment, Room } from "../types";
import { intervalErrors, toLocalInput, toUTC } from "../utils/dates";
export function BookingEditor({
  appointment,
  rooms,
  done,
}: {
  appointment?: Appointment;
  rooms: Room[];
  done: (a: Appointment) => void;
}) {
  const [params] = useSearchParams();
  const [roomId, setRoomId] = useState(
    String(appointment?.resource_id || params.get("sala") || ""),
  );
  const [start, setStart] = useState(
      appointment ? toLocalInput(appointment.starts_at) : "",
    ),
    [end, setEnd] = useState(
      appointment ? toLocalInput(appointment.ends_at) : "",
    );
  const submit = useSubmit();
  const room = rooms.find((r) => r.id === Number(roomId));
  return (
    <Form
      onSubmit={() =>
        submit.run(async () => {
          const errors = intervalErrors(start, end);
          if (!room?.is_active)
            errors.resource_id = "Selecione uma sala ativa.";
          if (Object.keys(errors).length) {
            submit.setFields(errors);
            return;
          }
          try {
            const times = { starts_at: toUTC(start), ends_at: toUTC(end) };
            done(
              await api<Appointment>(
                appointment
                  ? `/appointments/${appointment.id}`
                  : "/appointments",
                json(
                  appointment ? "PATCH" : "POST",
                  appointment
                    ? { action: "reschedule", ...times }
                    : { resource_id: Number(roomId), ...times },
                ),
              ),
            );
          } catch (e) {
            if (e instanceof ApiError && e.status === 409)
              throw new ApiError(
                "Horário indisponível ou sala inativa. Escolha outro horário; os dados foram mantidos.",
                409,
              );
            throw e;
          }
        })
      }
    >
      <div className="field">
        <label htmlFor="room">Sala</label>
        <select
          id="room"
          value={roomId}
          onChange={(e) => setRoomId(e.target.value)}
          required
          disabled={!!appointment}
          aria-invalid={!!submit.fields.resource_id}
          aria-describedby={
            submit.fields.resource_id ? "room-error" : undefined
          }
        >
          <option value="">Selecione uma sala</option>
          {rooms.map((r) => (
            <option key={r.id} value={r.id} disabled={!r.is_active}>
              {r.name}
              {!r.is_active && " (inativa)"}
            </option>
          ))}
        </select>
        {submit.fields.resource_id && (
          <span className="field-error" id="room-error">
            {submit.fields.resource_id}
          </span>
        )}
      </div>
      <TimeFields
        start={start}
        end={end}
        setStart={setStart}
        setEnd={setEnd}
        errors={submit.fields}
      />
      <Message>{submit.error}</Message>
      <div className="form-actions">
        <button className="primary" disabled={submit.busy || !room?.is_active}>
          {submit.busy
            ? "Salvando…"
            : appointment
              ? "Confirmar reagendamento"
              : "Confirmar reserva"}
        </button>
        {!room?.is_active && room && (
          <span>Sala inativa: reagendamento indisponível.</span>
        )}
      </div>
    </Form>
  );
}
export default function BookingForm() {
  const [rooms, setRooms] = useState<Room[]>([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  useEffect(() => {
    let active = true;
    api<Room[]>("/resources")
      .then((r) => {
        if (active) setRooms(r);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <>
      <PageTitle eyebrow="PLANEJE SEU ENCONTRO" title="Novo agendamento">
        Escolha uma sala e reserve o horário que funciona para você.
      </PageTitle>
      <div className="booking-layout">
        <section className="panel">
          <h2>Dados da reserva</h2>
          <Message>{error}</Message>
          {loading ? (
            <p role="status">Carregando salas…</p>
          ) : (
            !error && (
              <BookingEditor
                rooms={rooms}
                done={(a) =>
                  navigate(`/reservas/${a.id}`, {
                    state: { success: "Reserva criada com sucesso!" },
                  })
                }
              />
            )
          )}
        </section>
        <aside className="info-card">
          <span className="eyebrow">ANTES DE RESERVAR</span>
          <h2>Um encontro sem imprevistos.</h2>
          <p>Escolha um horário futuro, com o fim posterior ao início.</p>
          <p>
            A disponibilidade é confirmada ao salvar. Se outra pessoa reservar
            antes, você poderá escolher outro horário.
          </p>
          <Link to="/salas">Consultar salas e disponibilidade →</Link>
        </aside>
      </div>
    </>
  );
}
