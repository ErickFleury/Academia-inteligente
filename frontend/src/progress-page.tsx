import {
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  IconButton,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { ClientShell } from "./components/application-shell";
import { RouterButtonLink } from "./components/router-button-link";
import {
  EmptyState,
  LoadingState,
  PageHeader,
  StatusNotice,
} from "./components/ui";
import {
  createImageOnlyProgressUpdate,
  createProgressUpdate,
  deleteProgressUpdate,
  fetchProgressImage,
  getProgressFeed,
  replaceProgressImage,
  type ProgressUpdate,
} from "./progress";
import { setPostLike } from "./social";

const date = (value: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
const openPost = (postId: string) => {
  window.history.pushState({}, "", `/publicacoes/${postId}`);
  window.dispatchEvent(new PopStateEvent("popstate"));
};
function PostMedia({
  accessToken,
  post,
}: {
  accessToken: string;
  post: ProgressUpdate;
}) {
  const [urls, setUrls] = useState<string[]>([]);
  useEffect(() => {
    let active = true;
    let loaded: string[] = [];
    if (!post.images.length) {
      setUrls([]);
      return;
    }
    void Promise.all(
      post.images.map((image) =>
        fetchProgressImage(accessToken, post.id, image.id),
      ),
    )
      .then((values) => {
        loaded = values;
        if (active) setUrls(values);
        else values.forEach(URL.revokeObjectURL);
      })
      .catch(() => {
        if (active) setUrls([]);
      });
    return () => {
      active = false;
      loaded.forEach(URL.revokeObjectURL);
    };
  }, [accessToken, post.id, post.images]);
  if (!urls.length) return null;
  return (
    <Box
      aria-label={`Imagens da publicação de ${post.author_name}`}
      sx={{
        display: "grid",
        gap: 1,
        gridTemplateColumns:
          urls.length === 1 ? "1fr" : "repeat(2, minmax(0, 1fr))",
      }}
    >
      {urls.map((url, index) => (
        <Box
          key={post.images[index].id}
          sx={{
            aspectRatio: `${post.images[index].width} / ${post.images[index].height}`,
            bgcolor: "action.hover",
            borderRadius: 1,
            overflow: "hidden",
          }}
        >
          <Box
            alt={`Imagem ${index + 1} da publicação de ${post.author_name}`}
            component="img"
            loading="lazy"
            src={url}
            sx={{
              display: "block",
              height: "100%",
              objectFit: "cover",
              width: "100%",
            }}
          />
        </Box>
      ))}
    </Box>
  );
}
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
    [more, setMore] = useState(false);
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
            component="form"
            onSubmit={(event) => {
              event.preventDefault();
              void publish();
            }}
          >
            <CardContent>
              <Stack spacing={1.25}>
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
                    slotProps={{ htmlInput: { maxLength: 2000 } }}
                  />
                  <IconButton
                    aria-label={`Adicionar imagens (${files.length}/4)`}
                    component="label"
                  >
                    <span aria-hidden="true">+</span>
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
                <Button
                  disabled={!content.trim() && !files.length}
                  size="small"
                  sx={{ alignSelf: "flex-end" }}
                  type="submit"
                  variant="contained"
                >
                  Publicar atualização
                </Button>
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
              <Card
                component="article"
                key={item.id}
                onClick={() => openPost(item.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openPost(item.id);
                  }
                }}
                role="link"
                sx={{ cursor: "pointer" }}
                tabIndex={0}
              >
                <CardContent>
                  <Stack spacing={1}>
                    <Stack
                      direction="row"
                      spacing={1}
                      sx={{ alignItems: "center" }}
                    >
                      <Avatar>{item.author_name.slice(0, 1)}</Avatar>
                      {item.author_profile_id ? (
                        <RouterButtonLink
                          onClick={(event) => event.stopPropagation()}
                          to={`/perfis/${item.author_profile_id}`}
                          variant="text"
                        >
                          {item.author_name}
                        </RouterButtonLink>
                      ) : (
                        <Typography sx={{ fontWeight: 700 }}>
                          {item.author_name}
                        </Typography>
                      )}
                      <Typography color="text.secondary" variant="body2">
                        {date(item.created_at)}
                      </Typography>
                    </Stack>
                    {item.content && (
                      <Typography
                        sx={{
                          whiteSpace: "pre-wrap",
                          overflowWrap: "anywhere",
                        }}
                      >
                        {item.content}
                      </Typography>
                    )}
                    <PostMedia accessToken={accessToken} post={item} />
                    {item.edited_at && (
                      <Typography color="text.secondary" variant="caption">
                        editado
                      </Typography>
                    )}
                    <Stack direction="row">
                      <Button
                        aria-label={
                          item.liked_by_viewer
                            ? "Descurtir publicação"
                            : "Curtir publicação"
                        }
                        onClick={(event) => {
                          event.stopPropagation();
                          void toggleLike(item);
                        }}
                        variant="text"
                      >
                        {item.liked_by_viewer ? "♥" : "♡"} {item.like_count}
                      </Button>
                      <Button
                        aria-label="Abrir comentários"
                        onClick={(event) => {
                          event.stopPropagation();
                          openPost(item.id);
                        }}
                        variant="text"
                      >
                        💬 {item.comment_count}
                      </Button>
                    </Stack>
                    {item.is_own && (
                      <Button
                        color="error"
                        onClick={(event) => {
                          event.stopPropagation();
                          void deleteProgressUpdate(accessToken, item.id).then(
                            () =>
                              setItems(
                                (current) =>
                                  current?.filter(
                                    (value) => value.id !== item.id,
                                  ) ?? [],
                              ),
                          );
                        }}
                        size="small"
                      >
                        Excluir minha publicação
                      </Button>
                    )}
                  </Stack>
                </CardContent>
              </Card>
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
    </ClientShell>
  );
}
