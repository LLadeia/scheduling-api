import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, json } from "../api/client";
import { Field, Form, Message, PageTitle, useSubmit } from "../components/UI";
import TimeFields from "../components/TimeFields";
import type { Availability, Room } from "../types";
import { formatDate, intervalErrors, toUTC } from "../utils/dates";
const maxDays = Number(import.meta.env.VITE_AVAILABILITY_MAX_DAYS || 31);
export default function Rooms({ admin = false }: { admin?: boolean }) {
  const [rooms, setRooms] = useState<Room[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [reload, setReload] = useState(0);
  const [saved, setSaved] = useState("");
  const [editing, setEditing] = useState<Room | "new" | null>(null);
  const [selected, setSelected] = useState<Room | null>(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<Room[]>("/resources")
      .then((value) => {
        if (active) setRooms(value);
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
  }, [reload, admin]);
  return (
    <>
      <div className="title-row">
        <PageTitle
          eyebrow={admin ? "ADMINISTRAÇÃO" : "ENCONTRE SEU ESPAÇO"}
          title={admin ? "Gerenciar salas" : "Um espaço para cada encontro."}
        >
          {admin
            ? "Cadastre salas e mantenha as informações atualizadas."
            : "Explore as salas e consulte os horários disponíveis."}
        </PageTitle>
        {admin && (
          <button className="primary" onClick={() => setEditing("new")}>
            ＋ Cadastrar sala
          </button>
        )}
      </div>
      <div className="summary-strip">
        <span>
          <strong>{rooms.length}</strong> salas cadastradas
        </span>
        <span>
          <i className="dot" />
          {rooms.filter((r) => r.is_active).length} ativas
        </span>
        <Link to="/reservas/nova">Criar um agendamento →</Link>
      </div>
      <Message>{error}</Message>
      <Message success>{saved}</Message>
      {error && (
        <button onClick={() => setReload((x) => x + 1)}>
          Tentar novamente
        </button>
      )}
      {loading ? (
        <p role="status">Carregando salas…</p>
      ) : !rooms.length && !error ? (
        <div className="empty">
          Nenhuma sala cadastrada.
          {admin && " Use “Cadastrar sala” para começar."}
        </div>
      ) : (
        <div className="room-grid">
          {rooms.map((room, index) => (
            <article className="room-card" key={room.id}>
              <div className="room-cover">
                <span className="room-symbol">▦</span>
                <span className={`badge ${room.is_active ? "active" : ""}`}>
                  {room.is_active ? "Ativa" : "Inativa"}
                </span>
                <span className="room-number">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </div>
              <div className="room-body">
                <h2>{room.name}</h2>
                <p>{room.description || "Sem descrição cadastrada."}</p>
                <div className="card-actions">
                  <button onClick={() => setSelected(room)}>
                    Ver disponibilidade
                  </button>
                  {admin ? (
                    <button onClick={() => setEditing(room)}>Editar</button>
                  ) : room.is_active ? (
                    <Link
                      className="button primary"
                      to={`/reservas/nova?sala=${room.id}`}
                    >
                      Reservar →
                    </Link>
                  ) : (
                    <span className="muted">Indisponível para reservas</span>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
      {selected && (
        <section className="panel section-panel" aria-label="Disponibilidade">
          <div className="title-row">
            <h2>Disponibilidade · {selected.name}</h2>
            <button onClick={() => setSelected(null)}>Fechar</button>
          </div>
          <AvailabilityForm key={selected.id} room={selected} />
        </section>
      )}
      {editing && (
        <section className="panel section-panel" aria-label="Editar sala">
          <div className="title-row">
            <h2>
              {editing === "new"
                ? "Cadastrar sala"
                : `Editar · ${editing.name}`}
            </h2>
            <button onClick={() => setEditing(null)}>Fechar</button>
          </div>
          <RoomForm
            key={editing === "new" ? "new" : editing.id}
            room={editing === "new" ? undefined : editing}
            done={() => {
              setEditing(null);
              setSaved("Sala salva com sucesso.");
              setReload((x) => x + 1);
            }}
          />
        </section>
      )}
    </>
  );
}
function RoomForm({ room, done }: { room?: Room; done: () => void }) {
  const [name, setName] = useState(room?.name || ""),
    [description, setDescription] = useState(room?.description || ""),
    [active, setActive] = useState(room?.is_active ?? true);
  const submit = useSubmit();
  return (
    <Form
      onSubmit={() =>
        submit.run(async () => {
          if (!name.trim()) {
            submit.setFields({ name: "Informe o nome da sala." });
            return;
          }
          await api(
            room ? `/resources/${room.id}` : "/resources",
            json(room ? "PATCH" : "POST", {
              name: name.trim(),
              description: description || null,
              ...(room ? { is_active: active } : {}),
            }),
          );
          done();
        })
      }
    >
      <Message>{submit.error}</Message>
      <Field
        label="Nome"
        required
        maxLength={120}
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={submit.fields.name}
      />
      <div className="field">
        <label htmlFor="description">Descrição</label>
        <textarea
          id="description"
          maxLength={4000}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          aria-invalid={!!submit.fields.description}
          aria-describedby={
            submit.fields.description ? "description-error" : undefined
          }
        />
        {submit.fields.description && (
          <span className="field-error" id="description-error">
            {submit.fields.description}
          </span>
        )}
      </div>
      {room && (
        <label className="checkbox">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
          />{" "}
          Sala ativa para novas reservas
        </label>
      )}
      <button className="primary" disabled={submit.busy}>
        {submit.busy ? "Salvando…" : "Salvar sala"}
      </button>
    </Form>
  );
}
function AvailabilityForm({ room }: { room: Room }) {
  const [start, setStart] = useState(""),
    [end, setEnd] = useState(""),
    [result, setResult] = useState<Availability | null>(null);
  const submit = useSubmit();
  return (
    <>
      <p>
        Consulte uma janela de até {maxDays} dias. Consultar disponibilidade não
        garante a reserva.
      </p>
      <Form
        onSubmit={() =>
          submit.run(async () => {
            setResult(null);
            const errors = intervalErrors(start, end, false);
            if (Object.keys(errors).length) {
              submit.setFields(errors);
              return;
            }
            if (+new Date(end) - +new Date(start) > maxDays * 86400000) {
              submit.setFields({
                ends_at: `A janela máxima é de ${maxDays} dias.`,
              });
              return;
            }
            setResult(
              await api<Availability>(
                `/resources/${room.id}/availability?${new URLSearchParams({ starts_at: toUTC(start), ends_at: toUTC(end) })}`,
              ),
            );
          })
        }
      >
        <TimeFields
          start={start}
          end={end}
          setStart={(v) => {
            setStart(v);
            setResult(null);
          }}
          setEnd={(v) => {
            setEnd(v);
            setResult(null);
          }}
          errors={submit.fields}
        />
        <Message>{submit.error}</Message>
        <button className="primary" disabled={submit.busy}>
          {submit.busy ? "Consultando…" : "Consultar disponibilidade"}
        </button>
      </Form>
      {result && (
        <div role="status">
          <h3>Intervalos livres</h3>
          {!result.free_intervals.length ? (
            <p>Nenhum intervalo livre nesta janela.</p>
          ) : (
            <ul className="interval-list">
              {result.free_intervals.map((i) => (
                <li key={i.starts_at}>
                  {formatDate(i.starts_at)} → {formatDate(i.ends_at)}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  );
}
