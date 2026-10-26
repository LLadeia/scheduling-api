import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { AppRoutes } from "./App";
import { AuthProvider } from "./auth/Auth";
import { BookingEditor } from "./pages/BookingForm";
import { AppointmentDetail } from "./pages/Appointments";
import { ApiError, api, setToken } from "./api/client";
import { intervalErrors, toLocalInput, toUTC } from "./utils/dates";
const room = {
  id: 1,
  name: "Sala Azul",
  description: "Encontros",
  is_active: true,
};
const user = {
  id: 2,
  email: "cliente@example.com",
  role: "client",
  is_active: true,
};
const booking = {
  id: 8,
  user_id: 2,
  resource_id: 1,
  status: "scheduled",
  starts_at: "2035-01-10T13:00:00Z",
  ends_at: "2035-01-10T14:00:00Z",
};
function response(data: unknown, status = 200, headers = {}) {
  return new Response(data === undefined ? null : JSON.stringify(data), {
    status,
    headers,
  });
}
const fetchMock = vi.fn<typeof fetch>();
beforeEach(() => {
  setToken(null);
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});
function app(path = "/login") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Link to="/admin/salas">Abrir administração diretamente</Link>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}
async function login() {
  const u = userEvent.setup();
  await u.type(screen.getByLabelText("E-mail"), user.email);
  await u.type(screen.getByLabelText("Senha"), "senha-segura-123");
  await u.click(screen.getByRole("button", { name: /Entrar na minha conta/ }));
  return u;
}
describe("Autenticação e autorização", () => {
  it("envia login JSON, consulta perfil e navega para salas", async () => {
    fetchMock.mockImplementation(async (input) =>
      response(
        String(input).endsWith("/auth/login")
          ? { access_token: "test-token" }
          : String(input).endsWith("/users/me")
            ? user
            : [room],
      ),
    );
    app();
    await login();
    expect(
      await screen.findByText("Um espaço para cada encontro."),
    ).toBeInTheDocument();
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      email: user.email,
      password: "senha-segura-123",
    });
    expect(
      new Headers(fetchMock.mock.calls[1][1]?.headers).get("Authorization"),
    ).toBe("Bearer test-token");
  });
  it("apresenta mensagem genérica para credenciais inválidas", async () => {
    fetchMock.mockResolvedValue(response({ detail: "internal" }, 401));
    app();
    await login();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "E-mail ou senha inválidos.",
    );
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
  });
  it("impede visitante de entrar na administração", async () => {
    app("/admin/salas");
    expect(
      screen.getByRole("heading", { name: "Bom ter você aqui." }),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("impede cliente de acessar rota administrativa", async () => {
    fetchMock.mockImplementation(async (input) =>
      response(
        String(input).endsWith("/auth/login")
          ? { access_token: "test-token" }
          : String(input).endsWith("/users/me")
            ? user
            : [room],
      ),
    );
    app();
    await login();
    await screen.findByText("Um espaço para cada encontro.");
    expect(screen.queryByText("Gerenciar salas")).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("link", { name: "Abrir administração diretamente" }),
    );
    expect(
      await screen.findByText("Um espaço para cada encontro."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Gerenciar salas" }),
    ).not.toBeInTheDocument();
  });
});
describe("Reservas", () => {
  async function fill() {
    const u = userEvent.setup();
    await u.selectOptions(screen.getByLabelText("Sala"), "1");
    await u.type(screen.getByLabelText("Início"), "2035-01-10T10:00");
    await u.type(screen.getByLabelText("Fim"), "2035-01-10T11:00");
    return u;
  }
  it("envia criação sem proprietário e com UTC", async () => {
    const done = vi.fn();
    fetchMock.mockResolvedValue(response(booking, 201));
    render(
      <MemoryRouter>
        <BookingEditor rooms={[room]} done={done} />
      </MemoryRouter>,
    );
    const u = await fill();
    await u.click(screen.getByRole("button", { name: "Confirmar reserva" }));
    await waitFor(() => expect(done).toHaveBeenCalled());
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      resource_id: 1,
      starts_at: toUTC("2035-01-10T10:00"),
      ends_at: toUTC("2035-01-10T11:00"),
    });
  });
  it("mantém dados quando o servidor responde 409", async () => {
    fetchMock.mockResolvedValue(
      response({ detail: "Horário indisponível" }, 409),
    );
    render(
      <MemoryRouter>
        <BookingEditor rooms={[room]} done={vi.fn()} />
      </MemoryRouter>,
    );
    const u = await fill();
    await u.click(screen.getByRole("button", { name: "Confirmar reserva" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Horário indisponível",
    );
    expect(screen.getByLabelText("Início")).toHaveValue("2035-01-10T10:00");
  });
  it("envia apenas ação e datas no reagendamento", async () => {
    fetchMock.mockResolvedValue(response(booking));
    render(
      <MemoryRouter>
        <BookingEditor
          appointment={booking as never}
          rooms={[room]}
          done={vi.fn()}
        />
      </MemoryRouter>,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Confirmar reagendamento" }),
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(
      Object.keys(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).sort(),
    ).toEqual(["action", "ends_at", "starts_at"]);
  });
  it("só cancela após confirmação explícita", async () => {
    fetchMock.mockImplementation(async (input, init) =>
      response(
        String(input).endsWith("/resources")
          ? [room]
          : init?.method === "PATCH"
            ? { ...booking, status: "cancelled" }
            : booking,
      ),
    );
    render(
      <MemoryRouter initialEntries={["/reservas/8"]}>
        <Routes>
          <Route path="/reservas/:id" element={<AppointmentDetail />} />
        </Routes>
      </MemoryRouter>,
    );
    const u = userEvent.setup();
    await screen.findByText("Sala Azul");
    await u.click(screen.getByRole("button", { name: "Cancelar reserva" }));
    expect(
      fetchMock.mock.calls.filter((c) => c[1]?.method === "PATCH"),
    ).toHaveLength(0);
    await u.click(screen.getByRole("button", { name: "Manter reserva" }));
    expect(
      fetchMock.mock.calls.filter((c) => c[1]?.method === "PATCH"),
    ).toHaveLength(0);
    await u.click(screen.getByRole("button", { name: "Cancelar reserva" }));
    await u.click(
      screen.getByRole("button", { name: "Sim, cancelar reserva" }),
    );
    await screen.findByText("Reserva cancelada.");
    expect(
      JSON.parse(
        String(
          fetchMock.mock.calls.find((c) => c[1]?.method === "PATCH")?.[1]?.body,
        ),
      ),
    ).toEqual({ action: "cancel" });
  });
});
describe("Datas e comunicação HTTP", () => {
  it("converte de UTC para componentes locais sem truncar ISO", () => {
    const utc = "2035-01-10T13:00:00.000Z";
    const d = new Date(utc);
    const value = toLocalInput(utc);
    expect(Number(value.slice(11, 13))).toBe(d.getHours());
    expect(toUTC(value)).toBe(utc);
    expect(
      intervalErrors("2035-01-10T11:00", "2035-01-10T10:00").ends_at,
    ).toBeTruthy();
  });
  it("interpreta Retry-After e 422, e aceita resposta sem corpo", async () => {
    fetchMock
      .mockResolvedValueOnce(response({}, 429, { "Retry-After": "30" }))
      .mockResolvedValueOnce(
        response({ detail: [{ loc: ["body", "email"], msg: "invalid" }] }, 422),
      )
      .mockResolvedValueOnce(response(undefined, 204));
    await expect(api("/auth/login", {}, false)).rejects.toMatchObject({
      retryAfter: 30,
    });
    await expect(api("/auth/register", {}, false)).rejects.toMatchObject({
      fields: { email: "Informe um e-mail válido." },
    });
    await expect(api("/example")).resolves.toBeUndefined();
  });
  it("diferencia falha de conexão", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api("/resources")).rejects.toBeInstanceOf(ApiError);
    await expect(api("/resources")).rejects.toThrow(
      "Não foi possível conectar",
    );
  });
});
