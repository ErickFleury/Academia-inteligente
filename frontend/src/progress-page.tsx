import {
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { ClientShell } from "./components/application-shell";
import { WorkspaceIcon } from "./components/workspace-presentation";
import { PostCard } from "./post-card";
import { PostMedia } from "./post-media";
import {
  EmptyState,
  LoadingState,
  PageHeader,
  StatusNotice,
} from "./components/ui";
import {
  createImageOnlyProgressUpdate,
  deleteProgressImage,
  createProgressUpdate,
  deleteProgressUpdate,
  getProgressFeed,
  replaceProgressImage,
  type ProgressUpdate,
  updateProgressUpdate,
} from "./progress";
import { setPostLike } from "./social";

const openPost = (postId: string) => {
  window.history.pushState({}, "", `/publicacoes/${postId}`);
  window.dispatchEvent(new PopStateEvent("popstate"));
};
export function ProgressPage({
  accessToken,
  onSignOut,
}: {
  accessToken: string;
  onSignOut: () => void;
}) {
  const [items, setItems] = useState<ProgressUpdate[] | null>(null),
    [cursor, setCursor] = useState<string | null>(null),
    [end, setEnd] = useState(false),
    [content, setContent] = useState(""),
    [files, setFiles] = useState<File[]>([]),
    [error, setError] = useState<string | null>(null),
    [away, setAway] = useState(false),
    [more, setMore] = useState(false),
    [editing, setEditing] = useState<ProgressUpdate | null>(null),
    [editContent, setEditContent] = useState(""),
    [savingEdit, setSavingEdit] = useState(false);
  const composer = useRef<HTMLDivElement>(null),
    field = useRef<HTMLInputElement>(null),
    sentinel = useRef<HTMLDivElement>(null);
  const load = (next?: string | null) => {
    if (next && more) return;
    next ? setMore(true) : setItems(null);
    void getProgressFeed(accessToken, next ?? undefined)
      .then((page) => {
        setItems((old) =>
          next
            ? [
                ...(old ?? []),
                ...page.items.filter(
                  (value) =>
                    !(old ?? []).some((previous) => previous.id === value.id),
                ),
              ]
            : page.items,
        );
        setCursor(page.next_cursor);
        setEnd(page.end_reached);
      })
      .catch(() => setError("Não foi possível carregar as publicações."))
      .finally(() => setMore(false));
  };
  useEffect(() => {
    load();
  }, [accessToken]);
  useEffect(() => {
    if (!("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(([entry]) =>
      setAway(!entry.isIntersecting),
    );
    if (composer.current) observer.observe(composer.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && cursor && !end) load(cursor);
    });
    if (sentinel.current) observer.observe(sentinel.current);
    return () => observer.disconnect();
  }, [cursor, end, more]);
  async function publish() {
    if (!content.trim() && !files.length) return;
    try {
      let created = content.trim()
        ? await createProgressUpdate(accessToken, content.trim(), "shared")
        : await createImageOnlyProgressUpdate(accessToken, files[0], "shared");
      for (const [index, file] of files.entries())
        if (content.trim() || index > 0)
          created = await replaceProgressImage(
            accessToken,
            created.id,
            index,
            file,
          );
      setItems((old) => [created, ...(old ?? [])]);
      setContent("");
      setFiles([]);
    } catch {
      setError("Não foi possível publicar a publicação.");
    }
  }
  async function toggleLike(item: ProgressUpdate) {
    try {
      const detail = await setPostLike(
        accessToken,
        item.id,
        !item.liked_by_viewer,
      );
      setItems(
        (current) =>
          current?.map((value) =>
            value.id === item.id
              ? {
                  ...value,
                  like_count: detail.like_count,
                  liked_by_viewer: detail.liked_by_viewer,
                }
              : value,
          ) ?? [],
      );
    } catch {
      setError("Não foi possível atualizar a curtida.");
    }
  }
  function applyPostChange(updated: ProgressUpdate) {
    setItems(
      (current) =>
        current?.map((item) =>
          item.id === updated.id
            ? { ...item, ...updated, author_profile_id: item.author_profile_id }
            : item,
        ) ?? [],
    );
    setEditing((current) =>
      current?.id === updated.id
        ? { ...current, ...updated, author_profile_id: current.author_profile_id }
        : current,
    );
  }
  function openEditor(item: ProgressUpdate) {
    setEditing(item);
    setEditContent(item.content);
  }
  async function saveEdit() {
    if (!editing || (!editContent.trim() && !editing.images.length)) return;
    setSavingEdit(true);
    try {
      applyPostChange(
        await updateProgressUpdate(
          accessToken,
          editing.id,
          editContent.trim() || null,
        ),
      );
      setEditing(null);
    } catch {
      setError("Não foi possível salvar a publicação.");
    } finally {
      setSavingEdit(false);
    }
  }
  async function removeEditImage(imageId: string) {
    if (!editing) return;
    setSavingEdit(true);
    try {
      applyPostChange(
        await deleteProgressImage(accessToken, editing.id, imageId),
      );
    } catch {
      setError("A publicação precisa manter texto ou ao menos uma imagem.");
    } finally {
      setSavingEdit(false);
    }
  }
  async function addEditImages(selected: FileList | null) {
    if (!editing || !selected) return;
    const candidates = Array.from(selected).slice(
      0,
      4 - editing.images.length,
    );
    if (!candidates.length) return;
    setSavingEdit(true);
    try {
      let updated = editing;
      for (const file of candidates) {
        updated = await replaceProgressImage(
          accessToken,
          updated.id,
          updated.images.length,
          file,
        );
      }
      applyPostChange(updated);
    } catch {
      setError("Não foi possível adicionar a imagem à publicação.");
    } finally {
      setSavingEdit(false);
    }
  }
  async function deletePostFromEditor() {
    if (!editing) return;
    setSavingEdit(true);
    try {
      await deleteProgressUpdate(accessToken, editing.id);
      setItems((current) => current?.filter((item) => item.id !== editing.id) ?? []);
      setEditing(null);
    } catch {
      setError("Não foi possível deletar a publicação.");
    } finally {
      setSavingEdit(false);
    }
  }
  if (!items)
    return (
      <ClientShell onSignOut={onSignOut} showClientNavigation>
        <LoadingState label="Carregando publicações" />
      </ClientShell>
    );
  return (
    <ClientShell onSignOut={onSignOut} showClientNavigation>
      <Stack aria-busy={more} spacing={3} sx={{ maxWidth: 760, mx: "auto" }}>
        <PageHeader
          eyebrow="Feed"
          title="Publicações"
          description="Compartilhe somente o que desejar. Informações de saúde, pagamento, acesso e presença não são incluídas automaticamente."
        />
        <Box ref={composer}>
          <Card
            sx={{ borderColor: "rgba(255,133,100,0.3)" }}
            component="form"
            onSubmit={(event) => {
              event.preventDefault();
              void publish();
            }}
          >
            <CardContent>
              <Stack spacing={2}>
                <Typography component="h2" variant="h3">Compartilhe seu progresso</Typography>
                <Stack
                  direction="row"
                  spacing={0.5}
                  sx={{ alignItems: "flex-end" }}
                >
                  <TextField
                    inputRef={field}
                    fullWidth
                    label="Sua publicação"
                    multiline
                    minRows={2}
                    onChange={(event) => setContent(event.target.value)}
                    value={content}
                    slotProps={{
                      htmlInput: { maxLength: 2000 },
                      input: {
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton
                              aria-label={`Adicionar imagens (${files.length}/4)`}
                              component="label"
                              edge="end"
                            >
                              <WorkspaceIcon name="image" />
                              <input
                                accept="image/jpeg,image/png,image/webp"
                                hidden
                                multiple
                                type="file"
                                onChange={(event) =>
                                  setFiles(
                                    Array.from(event.target.files ?? []).slice(0, 4),
                                  )
                                }
                              />
                            </IconButton>
                          </InputAdornment>
                        ),
                      },
                    }}
                  />
                  <IconButton
                    aria-label="Publicar atualização"
                    disabled={!content.trim() && !files.length}
                    type="submit"
                    sx={{ bgcolor: "primary.main", color: "primary.contrastText", "&:hover": { bgcolor: "primary.light" } }}
                  >
                    <WorkspaceIcon name="send" />
                  </IconButton>
                </Stack>
                {files.map((file) => (
                  <Button
                    key={file.name + file.lastModified}
                    onClick={() =>
                      setFiles((current) =>
                        current.filter((value) => value !== file),
                      )
                    }
                    size="small"
                  >
                    Remover {file.name}
                  </Button>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Box>
        <Stack spacing={3}>
          {error && <StatusNotice severity="error">{error}</StatusNotice>}
          <Typography component="h2" variant="h3">
            Publicações recentes
          </Typography>
          {items.length === 0 ? (
            <EmptyState
              title="Nenhuma publicação compartilhada"
              description="Publique algo quando quiser."
            />
          ) : (
            items.map((item) => (
              <PostCard key={item.id} post={item} accessToken={accessToken}
                onOpen={() => openPost(item.id)} onLike={() => void toggleLike(item)}
                onEdit={item.is_own ? () => openEditor(item) : undefined} />
            ))
          )}
          <Box ref={sentinel} />
          {!end && (
            <Button
              disabled={more}
              onClick={() => cursor && load(cursor)}
              variant="outlined"
            >
              Carregar mais publicações
            </Button>
          )}
          {end && (
            <Typography aria-live="polite" color="text.secondary">
              Você chegou ao fim das publicações.
            </Typography>
          )}
        </Stack>
      </Stack>
      {away && (
        <Button
          onClick={() => {
            composer.current?.scrollIntoView({ behavior: "smooth" });
            setTimeout(() => field.current?.focus(), 250);
          }}
          sx={{ bottom: { xs: 76, sm: 24 }, position: "fixed", right: 16 }}
          variant="contained"
        >
          Criar publicação
        </Button>
      )}
      <Dialog
        fullWidth
        maxWidth="sm"
        onClose={() => !savingEdit && setEditing(null)}
        open={editing !== null}
      >
        <DialogTitle>Editar publicação</DialogTitle>
        <DialogContent>
          {editing && (
            <Stack spacing={2} sx={{ pt: 1 }}>
              <TextField
                autoFocus
                fullWidth
                label="Sua publicação"
                multiline
                minRows={3}
                onChange={(event) => setEditContent(event.target.value)}
                slotProps={{ htmlInput: { maxLength: 2000 } }}
                value={editContent}
              />
              <PostMedia
                accessToken={accessToken}
                onRemove={(imageId) => void removeEditImage(imageId)}
                post={editing}
              />
              {editing.images.length < 4 && (
                <IconButton
                  aria-label={`Adicionar imagens (${editing.images.length}/4)`}
                  component="label"
                  disabled={savingEdit}
                  sx={{ alignSelf: "flex-start" }}
                >
                  <WorkspaceIcon name="image" />
                  <input
                    accept="image/jpeg,image/png,image/webp"
                    hidden
                    multiple
                    type="file"
                    onChange={(event) => {
                      void addEditImages(event.target.files);
                      event.target.value = "";
                    }}
                  />
                </IconButton>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions sx={{ justifyContent: "space-between", px: 3, pb: 2 }}>
          <Button
            color="error"
            disabled={savingEdit}
            onClick={() => void deletePostFromEditor()}
            sx={{ "&:hover": { bgcolor: "error.main", color: "error.contrastText" } }}
          >
            Deletar post
          </Button>
          <Stack direction="row" spacing={1}>
            <Button disabled={savingEdit} onClick={() => setEditing(null)}>
              Cancelar
            </Button>
            <Button
              disabled={
                savingEdit ||
                !editing ||
                (!editContent.trim() && !editing.images.length)
              }
              onClick={() => void saveEdit()}
              variant="contained"
            >
              Salvar
            </Button>
          </Stack>
        </DialogActions>
      </Dialog>
    </ClientShell>
  );
}
