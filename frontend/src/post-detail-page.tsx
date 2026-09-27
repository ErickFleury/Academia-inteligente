import {
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ClientShell } from "./components/application-shell";
import { LoadingState, PageHeader, StatusNotice } from "./components/ui";
import { fetchProgressImage } from "./progress";
import {
  addPostComment,
  deletePostComment,
  fetchProfileImage,
  getPostDetail,
  setPostLike,
  type ProfileSummary,
  type PostDetail,
} from "./social";
import { RouterButtonLink } from "./components/router-button-link";

const date = (value: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

function ProfileAvatar({
  accessToken,
  profile,
  size = 40,
}: {
  accessToken: string;
  profile: ProfileSummary;
  size?: number;
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const name = profile.nickname || profile.name;

  useEffect(() => {
    if (!profile.has_image) {
      setImageUrl(null);
      return;
    }
    let active = true;
    let objectUrl: string | null = null;
    void fetchProfileImage(accessToken, profile.id)
      .then((url) => {
        objectUrl = url;
        if (active) setImageUrl(url);
        else URL.revokeObjectURL(url);
      })
      .catch(() => active && setImageUrl(null));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [accessToken, profile.has_image, profile.id]);

  return (
    <Avatar alt={`Foto de ${name}`} src={imageUrl ?? undefined} sx={{ height: size, width: size }}>
      {name.slice(0, 1)}
    </Avatar>
  );
}

function AuthorIdentity({
  accessToken,
  profile,
  timestamp,
}: {
  accessToken: string;
  profile: ProfileSummary;
  timestamp: string;
}) {
  const name = profile.nickname || profile.name;
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center", minWidth: 0 }}>
      <RouterButtonLink
        aria-label={`Abrir perfil de ${name}`}
        sx={{ justifyContent: "flex-start", minWidth: 0, p: 0.25 }}
        to={`/perfis/${profile.id}`}
        variant="text"
      >
        <ProfileAvatar accessToken={accessToken} profile={profile} />
        <Typography component="span" noWrap sx={{ fontWeight: 700, maxWidth: 220 }}>
          {name}
        </Typography>
      </RouterButtonLink>
      <Typography color="text.secondary" noWrap variant="body2">
        {date(timestamp)}
      </Typography>
    </Stack>
  );
}

function PostImages({
  accessToken,
  detail,
}: {
  accessToken: string;
  detail: PostDetail;
}) {
  const [urls, setUrls] = useState<string[]>([]);
  useEffect(() => {
    let active = true;
    let loaded: string[] = [];
    if (!detail.post.images.length) {
      setUrls([]);
      return;
    }
    void Promise.all(
      detail.post.images.map((image) =>
        fetchProgressImage(accessToken, detail.post.id, image.id),
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
  }, [accessToken, detail.post.id, detail.post.images]);
  if (!urls.length) return null;
  return (
    <Box
      aria-label="Imagens da publicação"
      sx={{
        display: "grid",
        gap: 1,
        gridTemplateColumns:
          urls.length === 1 ? "1fr" : "repeat(2, minmax(0, 1fr))",
      }}
    >
      {urls.map((url, index) => (
        <Box
          key={detail.post.images[index].id}
          sx={{
            aspectRatio: `${detail.post.images[index].width} / ${detail.post.images[index].height}`,
            bgcolor: "action.hover",
            borderRadius: 1,
            overflow: "hidden",
          }}
        >
          <Box
            alt={`Imagem ${index + 1} da publicação`}
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

export function PostDetailPage({
  accessToken,
  onSignOut,
  postId,
}: {
  accessToken: string;
  onSignOut: () => void;
  postId: string;
}) {
  const navigate = useNavigate();
  const [detail, setDetail] = useState<PostDetail | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = () => {
    void getPostDetail(accessToken, postId)
      .then(setDetail)
      .catch(() => setError("Não foi possível carregar a publicação."));
  };
  useEffect(load, [accessToken, postId]);
  async function like() {
    if (!detail) return;
    try {
      setDetail(
        await setPostLike(accessToken, postId, !detail.liked_by_viewer),
      );
    } catch {
      setError("Não foi possível atualizar a curtida.");
    }
  }
  async function publish() {
    try {
      await addPostComment(accessToken, postId, comment);
      setComment("");
      load();
    } catch {
      setError("Não foi possível publicar o comentário.");
    }
  }
  async function remove(id: string) {
    try {
      await deletePostComment(accessToken, id);
      load();
    } catch {
      setError("Não foi possível excluir o comentário.");
    }
  }
  return (
    <ClientShell onSignOut={onSignOut} showClientNavigation>
      <Stack spacing={3} sx={{ maxWidth: 760, mx: "auto" }}>
        <PageHeader
          action={
            <Button
              aria-label="Voltar"
              onClick={() => navigate(-1)}
              variant="text"
            >
              ←
            </Button>
          }
          eyebrow="Publicação"
          title="Detalhes da publicação"
        />
        {error && <StatusNotice severity="error">{error}</StatusNotice>}
        {!detail ? (
          <LoadingState label="Carregando publicação" />
        ) : (
          <>
            <Card>
              <CardContent>
                <Stack spacing={2}>
                  <AuthorIdentity
                    accessToken={accessToken}
                    profile={detail.author}
                    timestamp={detail.post.created_at}
                  />
                  {detail.post.content ? (
                    <Typography
                      sx={{ overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}
                    >
                      {detail.post.content}
                    </Typography>
                  ) : (
                    <Typography color="text.secondary">
                      Publicação com imagem.
                    </Typography>
                  )}
                  <PostImages accessToken={accessToken} detail={detail} />
                  <Button
                    onClick={() => void like()}
                    sx={{ alignSelf: "flex-start" }}
                    variant="outlined"
                  >
                    {detail.liked_by_viewer ? "♥" : "♡"} {detail.like_count}
                  </Button>
                </Stack>
              </CardContent>
            </Card>
            <Stack spacing={2}>
              <Typography
                component="h2"
                variant="h3"
              >
                Comentários
              </Typography>
              <Card
                component="form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void publish();
                }}
              >
                <CardContent>
                  <Stack spacing={1.5}>
                    <TextField
                      fullWidth
                      inputProps={{ maxLength: 2000 }}
                      label="Adicionar comentário"
                      multiline
                      minRows={2}
                      onChange={(event) => setComment(event.target.value)}
                      value={comment}
                    />
                    <Button
                      disabled={!comment.trim()}
                      type="submit"
                      variant="contained"
                    >
                      Enviar comentário
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
              <Stack spacing={2}>
                {detail.comments.map((item) => (
                  <Card component="article" key={item.id}>
                    <CardContent>
                      <Stack spacing={1}>
                        <AuthorIdentity
                          accessToken={accessToken}
                          profile={item.author}
                          timestamp={item.created_at}
                        />
                        {item.content && (
                          <Typography sx={{ whiteSpace: "pre-wrap" }}>
                            {item.content}
                          </Typography>
                        )}
                        {item.is_own && (
                          <Button
                            color="error"
                            onClick={() => void remove(item.id)}
                            size="small"
                            sx={{ alignSelf: "flex-start" }}
                            variant="text"
                          >
                            Excluir meu comentário
                          </Button>
                        )}
                      </Stack>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            </Stack>
          </>
        )}
      </Stack>
    </ClientShell>
  );
}
