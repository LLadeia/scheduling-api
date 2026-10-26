import { chromium } from "@playwright/test";
import crypto from "node:crypto";
import { mkdirSync } from "node:fs";
(async () => {
  if (!process.env.E2E_ADMIN_EMAIL || !process.env.E2E_ADMIN_PASSWORD)
    throw Error(
      "Configure E2E_ADMIN_EMAIL e E2E_ADMIN_PASSWORD fora do repositório.",
    );
  mkdirSync("test-results", { recursive: true });
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined,
    headless: true,
  });
  try {
    const context = await browser.newContext({
      timezoneId: "America/Sao_Paulo",
      viewport: { width: 1440, height: 1000 },
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const admin = {
      email: process.env.E2E_ADMIN_EMAIL,
      password: process.env.E2E_ADMIN_PASSWORD,
    };
    const room = "Sala Banca " + crypto.randomBytes(3).toString("hex");
    const client = {
      email:
        "cliente-" + crypto.randomBytes(5).toString("hex") + "@example.com",
      password: crypto.randomBytes(20).toString("hex"),
    };
    const click = async (name) =>
      page.getByRole("button", { name, exact: true }).click();
    const link = async (name) =>
      page.getByRole("link", { name, exact: true }).click();
    const fill = async (name, value) =>
      page.getByLabel(name, { exact: true }).fill(value);
    await page.goto(process.env.E2E_BASE_URL || "http://127.0.0.1:3000");
    await fill("E-mail", admin.email);
    await fill("Senha", admin.password);
    await click("Entrar na minha conta →");
    await page
      .getByRole("heading", { name: "Um espaço para cada encontro." })
      .waitFor();
    await link("⚙ Gerenciar salas");
    await click("＋ Cadastrar sala");
    await fill("Nome", room);
    await fill(
      "Descrição",
      "Sala de demonstração da banca, com espaço para discussão do projeto.",
    );
    await click("Salvar sala");
    await page.getByRole("heading", { name: room, exact: true }).waitFor();
    await page.screenshot({ path: "test-results/desktop.png", fullPage: true });
    await click("Sair");
    await link("Cadastre-se");
    await fill("E-mail", client.email);
    await fill("Senha", client.password);
    await click("Criar conta");
    await page
      .getByText("Conta criada. Entre com seu e-mail e senha.")
      .waitFor();
    await fill("E-mail", client.email);
    await fill("Senha", client.password);
    await click("Entrar na minha conta →");
    await page
      .getByRole("heading", { name: "Um espaço para cada encontro." })
      .waitFor();
    await page
      .getByRole("article")
      .filter({ has: page.getByRole("heading", { name: room, exact: true }) })
      .getByRole("link", { name: "Reservar →" })
      .click();
    await fill("Início", "2035-01-10T10:00");
    await fill("Fim", "2035-01-10T11:00");
    await click("Confirmar reserva");
    await page.getByText("Reserva criada com sucesso!").waitFor();
    await link("＋ Novo agendamento");
    await page
      .getByLabel("Sala", { exact: true })
      .selectOption({ label: room });
    await fill("Início", "2035-01-10T10:00");
    await fill("Fim", "2035-01-10T11:00");
    await click("Confirmar reserva");
    await page
      .getByRole("alert")
      .filter({ hasText: "Horário indisponível" })
      .waitFor();
    if (
      (await page.getByLabel("Início", { exact: true }).inputValue()) !==
      "2035-01-10T10:00"
    )
      throw Error("Dados não preservados");
    await link("▤ Meus agendamentos");
    await page
      .getByRole("link", { name: /Ver reserva/ })
      .first()
      .click();
    await click("Reagendar");
    if (
      (await page.getByLabel("Início", { exact: true }).inputValue()) !==
      "2035-01-10T10:00"
    )
      throw Error("Reagendamento não mostra fuso local");
    await fill("Início", "2035-01-10T12:00");
    await fill("Fim", "2035-01-10T13:00");
    await click("Confirmar reagendamento");
    await page.getByText("Reserva reagendada com sucesso!").waitFor();
    await click("Cancelar reserva");
    await click("Manter reserva");
    await click("Cancelar reserva");
    await click("Sim, cancelar reserva");
    await page.getByText("Reserva cancelada.", { exact: true }).waitFor();
    if (
      !(await page
        .getByRole("button", { name: "Reagendar", exact: true })
        .isDisabled())
    )
      throw Error("Cancelada permite reagendamento");
    await page.setViewportSize({ width: 390, height: 844 });
    await link("▦ Salas");
    await page
      .getByRole("heading", { name: "Um espaço para cada encontro." })
      .waitFor();
    await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
    if (
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      )
    )
      throw Error("Overflow horizontal mobile");
    await page.reload();
    await page.getByRole("heading", { name: "Bom ter você aqui." }).waitFor();
    if (errors.length) throw Error(errors.join("\n"));
    console.log(
      "PASS: admin login, cadastrar sala, cadastro/login cliente, criação, 409, reagendamento local/UTC, cancelar, mobile e sessão apenas em memória; sem erros JS.",
    );
  } finally {
    await browser.close();
  }
})().catch(() => {
  console.error(
    "Smoke de navegador falhou. Confira a aplicação, as credenciais locais e os seletores em scripts/browser-smoke.mjs.",
  );
  process.exit(1);
});
