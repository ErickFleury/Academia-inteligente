import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { ProgressPage } from "./progress-page";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("creates a progress update with image selection inside the composer", async () => {
  const createdPost = {
    author_name: "Ada",
    author_profile_id: null,
    comment_count: 0,
    content: "Treino concluído",
    created_at: "2026-09-23T12:00:00Z",
    edited_at: null,
    id: "update-1",
    image_count: 0,
    images: [],
    is_own: true,
    like_count: 0,
    liked_by_viewer: false,
    moderation_reason: null,
    moderation_status: "visible",
    updated_at: "2026-09-23T12:00:00Z",
    visibility: "private",
  };
  const fetchMock = vi.fn(async (input: string, init?: RequestInit) => {
    if (input.endsWith("/social-profiles/me"))
      return { ok: true, json: async () => ({ has_image: false, id: "profile-1", name: "Ada" }) };
    if (input.endsWith("/occupancy"))
      return { ok: true, json: async () => ({ occupancy: 1, status: "current", updated_at: null }) };
    if (input.includes("/progress?limit=20"))
      return { ok: true, json: async () => ({ items: [], next_cursor: null, end_reached: true }) };
    if (input.endsWith("/progress") && init?.method === "POST")
      return { ok: true, json: async () => createdPost };
    throw new Error(`Unexpected request: ${input}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<ProgressPage accessToken="token" onSignOut={vi.fn()} />);

  fireEvent.change(await screen.findByLabelText("Sua publicação"), {
    target: { value: "Treino concluído" },
  });
  expect(screen.getByRole("button", { name: "Adicionar imagens (0/4)" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Publicar atualização" }));

  expect(await screen.findByText("Treino concluído")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Editar publicação" }));
  expect(await screen.findByRole("dialog", { name: "Editar publicação" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Deletar post" })).toBeInTheDocument();
  expect(screen.queryByText("Visibilidade")).not.toBeInTheDocument();
  expect(
    fetchMock.mock.calls.find(
      ([url, init]) => String(url).endsWith("/progress") && init?.method === "POST",
    )?.[1],
  ).toMatchObject({ method: "POST", headers: { Authorization: "Bearer token" } });
});
