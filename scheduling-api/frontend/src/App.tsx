import {
  BrowserRouter,
  Link,
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/Auth";
import Login from "./pages/Login";
import Rooms from "./pages/Rooms";
import BookingForm from "./pages/BookingForm";
import Appointments, { AppointmentDetail } from "./pages/Appointments";
import { timezone } from "./utils/dates";
export function Protected({ admin = false }: { admin?: boolean }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin") return <Navigate to="/salas" replace />;
  return <Outlet />;
}
function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <a className="skip" href="#content">
        Pular para o conteúdo
      </a>
      <aside className="sidebar">
        <Link className="brand" to="/salas">
          <span className="brand-mark">A</span>AgendaSalas
        </Link>
        <div className="nav-label">SEU ESPAÇO</div>
        <nav aria-label="Navegação principal">
          <NavLink to="/salas">
            ▦ <span>Salas</span>
          </NavLink>
          <NavLink to="/reservas" end>
            ▤{" "}
            <span>
              {user?.role === "admin"
                ? "Todas as reservas"
                : "Meus agendamentos"}
            </span>
          </NavLink>
          <NavLink to="/reservas/nova">
            ＋ <span>Novo agendamento</span>
          </NavLink>
          {user?.role === "admin" && (
            <>
              <div className="nav-label">ADMINISTRAÇÃO</div>
              <NavLink to="/admin/salas">
                ⚙ <span>Gerenciar salas</span>
              </NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-foot">
          <strong>Encontros bem organizados.</strong>
          <p>Mais espaço para o que importa.</p>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="topbar-title">Organize seu próximo encontro</span>
          <div className="identity">
            <span className="avatar">{user?.email[0].toUpperCase()}</span>
            <div>
              <strong>{user?.email}</strong>
              <small>
                {user?.role === "admin" ? "Administrador" : "Cliente"}
              </small>
            </div>
            <button className="quiet" onClick={logout}>
              Sair
            </button>
          </div>
        </header>
        <main id="content" tabIndex={-1}>
          <Outlet />
        </main>
        <footer>
          AgendaSalas <span>Horários no fuso {timezone}</span>
        </footer>
      </div>
    </div>
  );
}
export function AppRoutes() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/cadastro" element={<Login key="register" register />} />
      <Route element={<Protected />}>
        <Route element={<Layout key={user?.id} />}>
          <Route path="/salas" element={<Rooms />} />
          <Route path="/reservas" element={<Appointments />} />
          <Route path="/reservas/nova" element={<BookingForm />} />
          <Route path="/reservas/:id" element={<AppointmentDetail />} />
          <Route element={<Protected admin />}>
            <Route path="/admin/salas" element={<Rooms admin />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/salas" replace />} />
    </Routes>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
