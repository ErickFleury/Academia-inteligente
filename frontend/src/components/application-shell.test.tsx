import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { AdminShell, ClientShell } from "./application-shell";

afterEach(cleanup);

test.each([
  ["administração", AdminShell],
  ["área do cliente", ClientShell],
])("the Sair button in %s submits logout exactly once", (_area, Shell) => {
  const onSignOut = vi.fn();
  render(<Shell onSignOut={onSignOut}>Conteúdo protegido</Shell>);

  const button = screen.getByRole("button", { name: "Sair" });
  fireEvent.click(button);
  fireEvent.click(button);

  expect(onSignOut).toHaveBeenCalledOnce();
  expect(button).toBeDisabled();
  expect(screen.getByRole("button", { name: "Saindo…" })).toBeDisabled();
});

test("client navigation uses the persistent sidebar shell on larger screens", () => {
  render(<ClientShell showClientNavigation>Conteúdo protegido</ClientShell>);

  expect(screen.getByRole("complementary")).toBeInTheDocument();
  expect(
    screen.getAllByRole("navigation", { name: "Navegação da área do cliente" }),
  ).toHaveLength(1);
  expect(screen.getAllByRole("link", { name: "Feed" })[0]).toHaveAttribute(
    "href",
    "/feed",
  );
  expect(screen.queryByRole("link", { name: "Ocupação" })).not.toBeInTheDocument();
  expect(screen.getByRole("status", { name: "Ocupação da academia indisponível" })).toBeInTheDocument();
  expect(screen.getByRole("main")).toHaveTextContent("Conteúdo protegido");
});

test("phone navigation opens in a collapsible side panel", () => {
  render(<ClientShell showClientNavigation>Conteúdo protegido</ClientShell>);

  fireEvent.click(screen.getByRole("button", { name: "Abrir navegação" }));

  expect(screen.getByRole("button", { name: "Fechar navegação" })).toBeInTheDocument();
  expect(
    screen.getByRole("navigation", { name: "Navegação da área do cliente" }),
  ).toHaveAttribute("id", "navegacao-cliente-movel");
  fireEvent.click(screen.getByRole("button", { name: "Fechar navegação" }));
  expect(screen.queryByRole("button", { name: "Fechar navegação" })).not.toBeInTheDocument();
});

test("admin sidebar retains every existing destination and its mobile menu", () => {
  render(<AdminShell onSignOut={() => {}}>Painel</AdminShell>);
  expect(screen.getByRole("navigation", { name: "Navegação da administração" })).toBeInTheDocument();
  for (const [name, href] of [["Painel administrativo", "/admin"], ["Acesso facial", "/admin/acesso-facial"], ["Gerenciar equipamentos", "/admin/equipamentos"], ["Moderar publicações", "/admin/publicacoes"]]) {
    expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
  }
  fireEvent.click(screen.getByRole("button", { name: "Abrir navegação" }));
  expect(screen.getByRole("navigation", { name: "Navegação da administração" })).toHaveAttribute("id", "navegacao-admin-movel");
  fireEvent.click(screen.getByRole("button", { name: "Fechar navegação" }));
  expect(screen.queryByRole("button", { name: "Fechar navegação" })).not.toBeInTheDocument();
});
