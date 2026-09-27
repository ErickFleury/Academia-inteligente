import {
  Avatar,
  Box,
  Button,
  ButtonBase,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { WorkspaceIcon } from "./components/workspace-presentation";
import { ClientShell } from "./components/application-shell";
import { RouterButtonLink } from "./components/router-button-link";
import {
  EmptyState,
  LoadingState,
  PageHeader,
  StatusNotice,
} from "./components/ui";
import {
  getOwnProfilePresence,
  updateOwnProfilePresence,
  type ProfilePresence,
} from "./profile-presence";
import { fetchProgressImage } from "./progress";
import {
  decideFollowRequest,
  fetchProfileImage,
  getFollowRequests,
  getOwnSocialProfile,
  getProfilePosts,
  getSocialProfile,
  followProfile,
  removeProfileImage,
  setPostLike,
  updateOwnSocialProfile,
  uploadProfileImage,
  type ProfileSummary,
  type SocialPost,
  type SocialProfile,
} from "./social";

const openPost = (postId: string) => {
  window.history.pushState({}, "", `/publicacoes/${postId}`);
  window.dispatchEvent(new PopStateEvent("popstate"));
};
function PostImages({
  accessToken,
  post,
}: {
  accessToken: string;
  post: SocialPost;
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
          key={post.images[index].id}
          sx={{
            aspectRatio: `${post.images[index].width} / ${post.images[index].height}`,
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

function PostCards({
  accessToken,
  posts,
  onLike,
}: {
  accessToken: string;
  posts: SocialPost[];
  onLike: (post: SocialPost) => void;
}) {
  if (!posts.length)
    return (
      <EmptyState
        title="Nenhuma publicação ainda"
        description="As publicações permitidas aparecerão aqui."
      />
    );
  return (
    <Stack spacing={2}>
      {posts.map((post) => (
        <Card
          component="article"
          key={post.id}
          onClick={() => openPost(post.id)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              openPost(post.id);
            }
          }}
          role="link"
          sx={{ cursor: "pointer" }}
          tabIndex={0}
        >
          <CardContent>
            <Stack spacing={1}>
              <Typography color="text.secondary" variant="body2">
                {new Intl.DateTimeFormat("pt-BR", {
                  dateStyle: "medium",
                  timeStyle: "short",
                }).format(new Date(post.created_at))}
              </Typography>
              {post.content && (
                <Typography
                  sx={{ overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}
                >
                  {post.content}
                </Typography>
              )}
              <PostImages accessToken={accessToken} post={post} />
              {post.moderation_status === "hidden" && (
                <StatusNotice severity="error">
                  Sua publicação foi ocultada: {post.moderation_reason}
                </StatusNotice>
              )}
              <Stack direction="row">
                <Button
                  aria-label={
                    post.liked_by_viewer
                      ? "Descurtir publicação"
                      : "Curtir publicação"
                  }
                  onClick={(event) => {
                    event.stopPropagation();
                    onLike(post);
                  }}
                  variant="text"
                  aria-pressed={post.liked_by_viewer}
                  sx={{ gap: 1, '& path': { fill: post.liked_by_viewer ? 'currentColor' : 'none' } }}
                >
                  <WorkspaceIcon name="heart" /> {post.like_count}
                </Button>
                <Button
                  aria-label="Abrir comentários"
                  onClick={(event) => {
                    event.stopPropagation();
                    openPost(post.id);
                  }}
                  variant="text"
                  sx={{ gap: 1 }}
                >
                  <WorkspaceIcon name="comment" /> {post.comment_count}
                </Button>
              </Stack>
            </Stack>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}

export function SocialProfilePage({
  accessToken,
  onSignOut,
  profileId,
}: {
  accessToken: string;
  onSignOut: () => void;
  profileId?: string;
}) {
  const ownProfileRoute = !profileId;
  const [profile, setProfile] = useState<SocialProfile | null>(null);
  const [posts, setPosts] = useState<SocialPost[] | null>(null);
  const [presence, setPresence] = useState<ProfilePresence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageRevision, setImageRevision] = useState(0);
  const [imageDialogOpen, setImageDialogOpen] = useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [requestsDialogOpen, setRequestsDialogOpen] = useState(false);
  const [requests, setRequests] = useState<ProfileSummary[]>([]);
  const input = useRef<HTMLInputElement>(null);
  const isOwner = ownProfileRoute || profile?.is_owner === true;
  const load = () => {
    setError(null);
    const profileRequest = ownProfileRoute
      ? getOwnSocialProfile(accessToken)
      : getSocialProfile(accessToken, profileId!);
    void profileRequest
      .then((item) => {
        setProfile(item);
        return getProfilePosts(accessToken, item.id);
      })
      .then(setPosts)
      .catch(() => {
        setError("Não foi possível carregar este perfil.");
        setPosts([]);
      });
  };
  useEffect(load, [accessToken, profileId]);
  useEffect(() => {
    if (isOwner)
      void getOwnProfilePresence(accessToken)
        .then(setPresence)
        .catch(() => undefined);
  }, [accessToken, isOwner]);
  useEffect(() => {
    if (!profile?.has_image) {
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
  }, [accessToken, imageRevision, profile?.has_image, profile?.id]);
  async function save(data: Parameters<typeof updateOwnSocialProfile>[1]) {
    setSaving(true);
    try {
      setProfile(await updateOwnSocialProfile(accessToken, data));
    } catch {
      setError("Não foi possível salvar o perfil.");
    } finally {
      setSaving(false);
    }
  }
  async function image(file?: File) {
    if (!file) return;
    if (
      file.size > 5 * 1024 * 1024 ||
      !["image/jpeg", "image/png", "image/webp"].includes(file.type)
    ) {
      setError("Escolha uma imagem JPEG, PNG ou WebP de até 5 MiB.");
      return;
    }
    setSaving(true);
    try {
      await uploadProfileImage(accessToken, file);
      setProfile(await getOwnSocialProfile(accessToken));
      setImageRevision((value) => value + 1);
      setImageDialogOpen(false);
    } catch {
      setError("Não foi possível enviar a imagem.");
    } finally {
      setSaving(false);
    }
  }
  async function toggleFollow() {
    if (!profile) return;
    try {
      setProfile(
        await followProfile(accessToken, profile.id, !profile.is_following),
      );
    } catch {
      setError("Não foi possível atualizar o acompanhamento.");
    }
  }
  async function openFollowRequests() {
    try {
      setRequests(await getFollowRequests(accessToken));
      setRequestsDialogOpen(true);
    } catch {
      setError("Não foi possível carregar as solicitações.");
    }
  }
  async function decideRequest(requester: ProfileSummary, accept: boolean) {
    try {
      await decideFollowRequest(accessToken, requester.id, accept);
      setRequests((current) =>
        current.filter((item) => item.id !== requester.id),
      );
      setProfile((current) =>
        current
          ? {
              ...current,
              pending_follow_request_count: Math.max(
                0,
                current.pending_follow_request_count - 1,
              ),
            }
          : current,
      );
    } catch {
      setError("Não foi possível responder à solicitação.");
    }
  }
  async function toggleLike(post: SocialPost) {
    try {
      const detail = await setPostLike(
        accessToken,
        post.id,
        !post.liked_by_viewer,
      );
      setPosts(
        (current) =>
          current?.map((item) =>
            item.id === post.id
              ? {
                  ...item,
                  like_count: detail.like_count,
                  liked_by_viewer: detail.liked_by_viewer,
                }
              : item,
          ) ?? [],
      );
    } catch {
      setError("Não foi possível atualizar a curtida.");
    }
  }
  async function removeImage() {
    setSaving(true);
    try {
      await removeProfileImage(accessToken);
      setProfile(await getOwnSocialProfile(accessToken));
      setImageRevision((value) => value + 1);
      setImageDialogOpen(false);
    } catch {
      setError("Não foi possível remover a imagem.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <ClientShell onSignOut={onSignOut} showClientNavigation>
      <Stack spacing={3} sx={{ maxWidth: 800, minWidth: 0, mx: "auto" }}>
        <PageHeader
          eyebrow={isOwner ? "Meu perfil" : "Perfil"}
          title={profile ? profile.nickname || profile.name : "Perfil"}
          description={
            isOwner
              ? "Seu perfil social é visível apenas para outros clientes autenticados enquanto esta opção estiver ativada."
              : "Publicações e informações permitidas deste cliente."
          }
        />
        {error && <StatusNotice severity="error">{error}</StatusNotice>}
        {!profile || !posts ? (
          <LoadingState label="Carregando perfil" />
        ) : (
          <>
            <Card component="section" sx={{ borderTop: "3px solid", borderTopColor: "primary.main" }}>
              <CardContent>
                <Stack spacing={2.5}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={2}
                    sx={{ alignItems: { sm: "center" } }}
                  >
                    {isOwner ? (
                      <ButtonBase
                        aria-label="Gerenciar foto de perfil"
                        disabled={saving}
                        onClick={() => setImageDialogOpen(true)}
                        sx={{ borderRadius: "50%", height: 96, width: 96 }}
                      >
                        <Avatar
                          alt={`Foto de ${profile.name}`}
                          src={imageUrl ?? undefined}
                          sx={{ height: 96, width: 96, bgcolor: "rgba(255,133,100,0.12)", color: "primary.main", fontSize: "2rem", border: "3px solid", borderColor: "divider" }}
                        >
                          {profile.name.slice(0, 1)}
                        </Avatar>
                      </ButtonBase>
                    ) : (
                      <Avatar
                        alt={`Foto de ${profile.name}`}
                        src={imageUrl ?? undefined}
                        sx={{ height: 96, width: 96, bgcolor: "rgba(255,133,100,0.12)", color: "primary.main", fontSize: "2rem", border: "3px solid", borderColor: "divider" }}
                      >
                        {profile.name.slice(0, 1)}
                      </Avatar>
                    )}
                    <Stack spacing={0.5} sx={{ minWidth: 0, flexGrow: 1 }}>
                      <Typography component="h2" variant="h3">
                        {profile.name}
                      </Typography>
                      {profile.nickname && (
                        <Typography color="text.secondary">
                          {profile.nickname}
                        </Typography>
                      )}
                      {profile.currently_present && (
                        <Chip
                          color="success"
                          label="Na academia"
                          sx={{ alignSelf: "flex-start", fontWeight: 700 }}
                        />
                      )}
                    </Stack>
                    {isOwner ? (
                      <Stack direction="row">
                        <IconButton
                          aria-label="Configurações do perfil"
                          onClick={() => setSettingsDialogOpen(true)}
                        >
                          <WorkspaceIcon name="settings" />
                        </IconButton>
                      </Stack>
                    ) : (
                      <Button
                        disabled={profile.follow_requested}
                        onClick={() => void toggleFollow()}
                        variant={
                          profile.is_following ? "outlined" : "contained"
                        }
                      >
                        {profile.is_following
                          ? "Deixar de seguir"
                          : profile.follow_requested
                            ? "Solicitação enviada"
                            : "Seguir"}
                      </Button>
                    )}
                  </Stack>
                  {isOwner ? (
                    <>
                      <TextField
                        fullWidth
                        label="Apelido"
                        value={profile.nickname ?? ""}
                        onBlur={(event) =>
                          void save({ nickname: event.target.value })
                        }
                        onChange={(event) =>
                          setProfile({
                            ...profile,
                            nickname: event.target.value || null,
                          })
                        }
                        slotProps={{ htmlInput: { maxLength: 40 } }}
                      />
                      <TextField
                        fullWidth
                        label="Biografia"
                        multiline
                        minRows={2}
                        value={profile.biography ?? ""}
                        onBlur={(event) =>
                          void save({ biography: event.target.value })
                        }
                        onChange={(event) =>
                          setProfile({
                            ...profile,
                            biography: event.target.value || null,
                          })
                        }
                        slotProps={{ htmlInput: { maxLength: 160 } }}
                      />
                      {profile.biography_moderation_status === "hidden" && (
                        <StatusNotice severity="error">
                          Sua biografia foi ocultada:{" "}
                          {profile.biography_moderation_reason}
                        </StatusNotice>
                      )}
                      <input
                        accept="image/jpeg,image/png,image/webp"
                        aria-label="Enviar foto de perfil"
                        hidden
                        onChange={(event) =>
                          void image(event.target.files?.[0])
                        }
                        ref={input}
                        type="file"
                      />
                    </>
                  ) : (
                    profile.biography && (
                      <Typography sx={{ whiteSpace: "pre-wrap" }}>
                        {profile.biography}
                      </Typography>
                    )
                  )}
                  <Stack direction="row" spacing={2} useFlexGap sx={{ alignItems: "center", flexWrap: "wrap", borderTop: "1px solid", borderColor: "divider", pt: 2 }}>
                    <Typography>{profile.follower_count} seguidores</Typography>
                    {isOwner && profile.pending_follow_request_count > 0 && (
                      <IconButton
                        aria-label={`${profile.pending_follow_request_count} solicitações para seguir`}
                        onClick={() => void openFollowRequests()}
                        size="small"
                        sx={{ color: "error.main" }}
                      >
                        <span aria-hidden="true">!</span>
                      </IconButton>
                    )}
                    <Typography>{profile.following_count} seguindo</Typography>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
            <Dialog
              aria-labelledby="foto-perfil-titulo"
              onClose={() => setImageDialogOpen(false)}
              open={imageDialogOpen}
            >
              <DialogTitle id="foto-perfil-titulo">Foto de perfil</DialogTitle>
              <DialogContent>
                <Typography color="text.secondary">
                  Escolha uma imagem JPEG, PNG ou WebP de até 5 MiB.
                </Typography>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setImageDialogOpen(false)}>
                  Cancelar
                </Button>
                {profile.has_image && (
                  <Button
                    color="error"
                    disabled={saving}
                    onClick={() => void removeImage()}
                  >
                    Remover foto
                  </Button>
                )}
                <Button
                  disabled={saving}
                  onClick={() => input.current?.click()}
                  variant="contained"
                >
                  {profile.has_image ? "Editar foto" : "Adicionar foto"}
                </Button>
              </DialogActions>
            </Dialog>
            {isOwner && (
              <Dialog
                aria-labelledby="configuracoes-perfil-titulo"
                onClose={() => setSettingsDialogOpen(false)}
                open={settingsDialogOpen}
              >
                <DialogTitle id="configuracoes-perfil-titulo">
                  Configurações do perfil
                </DialogTitle>
                <DialogContent>
                  <Stack spacing={1}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={profile.visible_to_clients ?? true}
                          disabled={saving}
                          onChange={(event) =>
                            void save({
                              visible_to_clients: event.target.checked,
                            })
                          }
                        />
                      }
                      label="Conta pública"
                    />
                    {presence && (
                      <FormControlLabel
                        control={
                          <Switch
                            checked={presence.sharing_enabled}
                            disabled={saving}
                            onChange={(event) =>
                              void updateOwnProfilePresence(
                                accessToken,
                                event.target.checked,
                              ).then(setPresence)
                            }
                          />
                        }
                        label="Mostrar no meu perfil quando eu estiver na academia"
                      />
                    )}
                    <Typography color="text.secondary" variant="body2">
                      A presença começa desativada e é independente da
                      visibilidade do perfil.
                    </Typography>
                  </Stack>
                </DialogContent>
                <DialogActions>
                  <Button onClick={() => setSettingsDialogOpen(false)}>
                    Concluído
                  </Button>
                </DialogActions>
              </Dialog>
            )}
            {isOwner && (
              <Dialog
                aria-labelledby="solicitacoes-seguir-titulo"
                onClose={() => setRequestsDialogOpen(false)}
                open={requestsDialogOpen}
              >
                <DialogTitle id="solicitacoes-seguir-titulo">
                  Solicitações para seguir
                </DialogTitle>
                <DialogContent>
                  <Stack spacing={1}>
                    {requests.length ? (
                      requests.map((request) => (
                        <Stack
                          direction="row"
                          key={request.id}
                          spacing={2}
                          sx={{ alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 1 }}
                        >
                          <Typography>
                            {request.nickname || request.name}
                          </Typography>
                          <Stack direction="row">
                            <Button
                              onClick={() => void decideRequest(request, false)}
                            >
                              Recusar
                            </Button>
                            <Button
                              onClick={() => void decideRequest(request, true)}
                              variant="contained"
                            >
                              Aceitar
                            </Button>
                          </Stack>
                        </Stack>
                      ))
                    ) : (
                      <Typography color="text.secondary">
                        Nenhuma solicitação pendente.
                      </Typography>
                    )}
                  </Stack>
                </DialogContent>
              </Dialog>
            )}
            <Typography component="h2" variant="h3">
              Publicações
            </Typography>
            <PostCards
              accessToken={accessToken}
              onLike={(post) => void toggleLike(post)}
              posts={posts}
            />
          </>
        )}
      </Stack>
    </ClientShell>
  );
}
