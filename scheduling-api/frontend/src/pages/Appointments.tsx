import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { api, json } from "../api/client";
import { useAuth } from "../auth/Auth";
import { Field, Form, Message, PageTitle, useSubmit } from "../components/UI";
import { BookingEditor } from "./BookingForm";
import type { Appointment, AppointmentPage, Room } from "../types";
import { formatDate, toUTC } from "../utils/dates";
function Badge({ status }: { status: Appointment["status"] }) {
  return (
    <span className={`badge ${status === "scheduled" ? "active" : ""}`}>
      {status === "scheduled" ? "Agendada" : "Cancelada"}
    </span>
  );
}
export default function Appointments() {
  const { user } = useAuth();
  const [rooms, setRooms] = useState<Room[]>([]),
    [data, setData] = useState<AppointmentPage | null>(null),
    [page, setPage] = useState(1),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [from, setFrom] = useState(""),
    [before, setBefore] = useState(""),
    [status, setStatus] = useState(""),
    [userId, setUserId] = useState(""),
    [filters, setFilters] = useState(""),
    [filterError, setFilterError] = useState(""),
    [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      api<AppointmentPage>(`/appointments?page=${page}&limit=10${filters}`),
      api<Room[]>("/resources"),
    ])
      .then(([result, list]) => {
        if (active) {
          setData(result);
          setRooms(list);
        }
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
  }, [page, filters, retry]);
  const names = new Map(rooms.map((r) => [r.id, r.name]));
  return (
    <>
      <div className="title-row">
        <PageTitle
          eyebrow="SUA AGENDA"
          title={
            user?.role === "admin" ? "Todas as reservas" : "Meus agendamentos"
          }
        >
          Acompanhe seus encontros e ajuste seus planos.
        </PageTitle>
        <Link className="button primary" to="/reservas/nova">
          ＋ Novo agendamento
        </Link>
      </div>
      <section className="panel filters">
        <Form
          onSubmit={() => {
            setFilterError("");
            if (from && before && +new Date(before) <= +new Date(from)) {
              setFilterError("O limite final deve ser posterior ao inicial.");
              return;
            }
            const q = new URLSearchParams();
            if (from) q.set("starts_from", toUTC(from));
            if (before) q.set("starts_before", toUTC(before));
            if (status) q.set("status", status);
            if (userId && user?.role === "admin") q.set("user_id", userId);
            setPage(1);
            setFilters(q.size ? `&${q}` : "");
          }}
        >
          <div className="filter-grid">
            <Field
              label="Início a partir de (inclusive)"
              type="datetime-local"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
            <Field
              label="Início antes de (exclusivo)"
              type="datetime-local"
              value={before}
              onChange={(e) => setBefore(e.target.value)}
            />
            <div className="field">
              <label htmlFor="status">Situação</label>
              <select
                id="status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="">Todas</option>
                <option value="scheduled">Agendada</option>
                <option value="cancelled">Cancelada</option>
              </select>
            </div>
            {user?.role === "admin" && (
              <Field
                label="ID do usuário"
                type="number"
                min={1}
                step={1}
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
              />
            )}
            <button disabled={loading}>Aplicar filtros</button>
          </div>
          <Message>{filterError}</Message>
        </Form>
        <p className="hint">
          Os filtros selecionam o início da reserva, não todos os horários que
          cruzam o intervalo.
        </p>
      </section>
      <Message>{error}</Message>
      {error && (
        <button onClick={() => setRetry((x) => x + 1)}>Tentar novamente</button>
      )}
      {loading ? (
        <p role="status">Carregando agendamentos…</p>
      ) : (
        !error &&
        data && (
          <section className="panel table-panel">
            <div className="list-heading">
              <h2>Agendamentos</h2>
              <span>
                {data.total} {data.total === 1 ? "reserva" : "reservas"}
              </span>
            </div>
            {data.items.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Sala</th>
                      <th>Início</th>
                      <th>Fim</th>
                      <th>Situação</th>
                      {user?.role === "admin" && <th>Usuário</th>}
                      <th>
                        <span className="sr-only">Ações</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <strong>
                            {names.get(a.resource_id) ||
                              `Sala #${a.resource_id}`}
                          </strong>
                          <small>Reserva #{a.id}</small>
                        </td>
                        <td>{formatDate(a.starts_at)}</td>
                        <td>{formatDate(a.ends_at)}</td>
                        <td>
                          <Badge status={a.status} />
                        </td>
                        {user?.role === "admin" && <td>#{a.user_id}</td>}
                        <td>
                          <Link
                            aria-label={`Ver reserva ${a.id}`}
                            to={`/reservas/${a.id}`}
                          >
                            Detalhes →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty">
                Nenhum agendamento encontrado. Experimente ajustar os filtros ou
                criar sua primeira reserva.
              </div>
            )}
            <nav className="pagination" aria-label="Paginação">
              <span>
                Página {data.page} de{" "}
                {Math.max(1, Math.ceil(data.total / data.limit))}
              </span>
              <div>
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  ← Anterior
                </button>
                <button
                  disabled={page * data.limit >= data.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Próxima →
                </button>
              </div>
            </nav>
          </section>
        )
      )}
    </>
  );
}
export function AppointmentDetail() {
  const { id } = useParams(),
    location = useLocation(),
    submit = useSubmit();
  const [appointment, setAppointment] = useState<Appointment | null>(null),
    [rooms, setRooms] = useState<Room[]>([]),
    [error, setError] = useState(""),
    [edit, setEdit] = useState(false),
    [confirm, setConfirm] = useState(false),
    [success, setSuccess] = useState<string>(location.state?.success || ""),
    [retry, setRetry] = useState(0);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    let active = true;
    setAppointment(null);
    setError("");
    Promise.all([
      api<Appointment>(`/appointments/${id}`),
      api<Room[]>("/resources"),
    ])
      .then(([a, r]) => {
        if (active) {
          setAppointment(a);
          setRooms(r);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [id, retry]);
  useEffect(() => {
    if (confirm) dialog.current?.showModal();
    else dialog.current?.close();
  }, [confirm]);
  const room = rooms.find((r) => r.id === appointment?.resource_id);
  const mutable =
    appointment?.status === "scheduled" &&
    +new Date(appointment.starts_at) > Date.now();
  return (
    <>
      <Link className="back-link" to="/reservas">
        ← Voltar para agendamentos
      </Link>
      <PageTitle eyebrow="DETALHES DO ENCONTRO" title={`Reserva #${id}`} />
      <Message>{error}</Message>
      {error && (
        <button onClick={() => setRetry((x) => x + 1)}>Tentar novamente</button>
      )}
      <Message success>{success}</Message>
      {!appointment && !error && <p role="status">Carregando reserva…</p>}
      {appointment && (
        <section className="panel detail-panel">
          <div className="title-row">
            <h2>{room?.name || `Sala #${appointment.resource_id}`}</h2>
            <Badge status={appointment.status} />
          </div>
          <dl>
            <div>
              <dt>Início</dt>
              <dd>{formatDate(appointment.starts_at)}</dd>
            </div>
            <div>
              <dt>Fim</dt>
              <dd>{formatDate(appointment.ends_at)}</dd>
            </div>
            <div>
              <dt>Responsável</dt>
              <dd>Usuário #{appointment.user_id}</dd>
            </div>
          </dl>
          {!mutable && (
            <p className="hint">
              {appointment.status === "cancelled"
                ? "O cancelamento é definitivo. Esta reserva não pode ser reagendada."
                : "Esta reserva já começou. Alterações não estão mais disponíveis."}
            </p>
          )}
          <Message>{submit.error}</Message>
          <div className="form-actions">
            <button
              disabled={!mutable || !room?.is_active || submit.busy}
              onClick={() => {
                setEdit(!edit);
                setSuccess("");
              }}
            >
              Reagendar
            </button>
            <button
              className="danger"
              disabled={!mutable || submit.busy}
              onClick={() => setConfirm(true)}
            >
              Cancelar reserva
            </button>
          </div>
          {mutable && !room?.is_active && (
            <p>
              Sala inativa: não é possível reagendar. Você ainda pode cancelar.
            </p>
          )}
          {edit && mutable && (
            <div className="section-panel">
              <h3>Reagendar encontro</h3>
              <BookingEditor
                appointment={appointment}
                rooms={rooms}
                done={(a) => {
                  setAppointment(a);
                  setEdit(false);
                  setSuccess("Reserva reagendada com sucesso!");
                }}
              />
            </div>
          )}
        </section>
      )}
      <dialog
        ref={dialog}
        onCancel={(e) => {
          e.preventDefault();
          if (!submit.busy) setConfirm(false);
        }}
        aria-labelledby="cancel-title"
      >
        <h2 id="cancel-title">Cancelar esta reserva?</h2>
        <p>
          O cancelamento é definitivo. O horário será liberado para outras
          pessoas.
        </p>
        <div className="form-actions">
          <button
            autoFocus
            disabled={submit.busy}
            onClick={() => setConfirm(false)}
          >
            Manter reserva
          </button>
          <button
            className="danger"
            disabled={submit.busy}
            onClick={() =>
              submit.run(async () => {
                try {
                  setAppointment(
                    await api<Appointment>(
                      `/appointments/${id}`,
                      json("PATCH", { action: "cancel" }),
                    ),
                  );
                  setSuccess("Reserva cancelada.");
                  setEdit(false);
                } finally {
                  setConfirm(false);
                }
              })
            }
          >
            {submit.busy ? "Cancelando…" : "Sim, cancelar reserva"}
          </button>
        </div>
      </dialog>
    </>
  );
}
