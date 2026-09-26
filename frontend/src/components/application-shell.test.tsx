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
  ).toHaveLength(2);
  expect(screen.getAllByRole("link", { name: "Feed" })[0]).toHaveAttribute(
    "href",
    "/feed",
  );
  expect(screen.getByRole("main")).toHaveTextContent("Conteúdo protegido");
});
