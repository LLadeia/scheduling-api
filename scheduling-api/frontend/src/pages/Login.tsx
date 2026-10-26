import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useLocation } from "react-router-dom";
import { ApiError, api, json } from "../api/client";
import { useAuth } from "../auth/Auth";
import { Field, Form, Message, useSubmit } from "../components/UI";
export default function Login({ register = false }: { register?: boolean }) {
  const currentLocation = useLocation();
  const auth = useAuth(),
    navigate = useNavigate(),
    submit = useSubmit();
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [wait, setWait] = useState(0);
  useEffect(() => {
    if (wait <= 0) return;
    const timer = setTimeout(() => setWait(wait - 1), 1000);
    return () => clearTimeout(timer);
  }, [wait]);
  if (auth.user) return <Navigate to="/salas" replace />;
  return (
    <main className="auth-page">
      <section className="auth-story">
        <Link className="brand" to="/login">
          <span className="brand-mark">A</span>AgendaSalas
        </Link>
        <div>
          <span className="eyebrow">ESPAÇO PARA SUAS IDEIAS</span>
          <h1>
            Seu próximo encontro
            <br />
            começa aqui.
          </h1>
          <p>
            Encontre uma sala, escolha o melhor horário e organize seus
            encontros em um só lugar.
          </p>
          <div className="story-line">
            01 <span>Escolha a sala</span>
          </div>
          <div className="story-line">
            02 <span>Reserve seu horário</span>
          </div>
          <div className="story-line">
            03 <span>Prepare seu encontro</span>
          </div>
        </div>
        <small>Agendamento de salas · TFG</small>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <span className="eyebrow">BEM-VINDO AO AGENDASALAS</span>
          <h2>{register ? "Crie sua conta" : "Bom ter você aqui."}</h2>
          <p>
            {register
              ? "Cadastre-se para reservar salas."
              : "Entre para organizar seus agendamentos."}
          </p>
          <Message>{submit.error || auth.reason}</Message>
          <Form
            onSubmit={() =>
              submit.run(async () => {
                try {
                  if (register) {
                    await api(
                      "/auth/register",
                      json("POST", { email, password }),
                      false,
                    );
                    navigate("/login?cadastro=ok");
                    return;
                  }
                  await auth.login(email, password);
                  navigate("/salas");
                } catch (e) {
                  if (e instanceof ApiError && e.status === 429)
                    setWait(e.retryAfter || 60);
                  throw e;
                }
              })
            }
          >
            <Field
              label="E-mail"
              type="email"
              autoComplete="email"
              required
              maxLength={254}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={submit.fields.email}
            />
            <Field
              label="Senha"
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              required
              minLength={register ? 12 : 1}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={submit.fields.password}
            />
            {register && <small>Use entre 12 e 128 caracteres.</small>}
            <button className="primary full" disabled={submit.busy || wait > 0}>
              {submit.busy
                ? "Aguarde…"
                : wait
                  ? `Aguarde ${wait}s`
                  : register
                    ? "Criar conta"
                    : "Entrar na minha conta →"}
            </button>
          </Form>
          {!register && currentLocation.search.includes("cadastro=ok") && (
            <Message success>
              Conta criada. Entre com seu e-mail e senha.
            </Message>
          )}
          <p className="auth-switch">
            {register ? "Já tem uma conta?" : "Ainda não tem conta?"}{" "}
            <Link to={register ? "/login" : "/cadastro"}>
              {register ? "Entrar" : "Cadastre-se"}
            </Link>
          </p>
          <small className="muted">
            Sua sessão é encerrada ao recarregar a página.
          </small>
        </div>
      </section>
    </main>
  );
}
