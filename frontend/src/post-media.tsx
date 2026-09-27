import { Box, IconButton, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { fetchProgressImage, type ProgressUpdate } from "./progress";

export function PostMedia({
  accessToken,
  onRemove,
  post,
  fetchImage = fetchProgressImage,
  description,
}: {
  accessToken: string;
  onRemove?: (imageId: string) => void;
  post: Pick<ProgressUpdate, "id" | "images" | "author_name">;
  description?: string;
  fetchImage?: typeof fetchProgressImage;
}) {
  const [failed, setFailed] = useState(false);
  const [urls, setUrls] = useState<string[]>([]);
  useEffect(() => {
    let active = true;
    setFailed(false);
    let loaded: string[] = [];
    if (!post.images.length) {
      setUrls([]);
      return;
    }
    void Promise.all(
      post.images.map((image) =>
        fetchImage(accessToken, post.id, image.id),
      ),
    )
      .then((values) => {
        loaded = values;
        if (active) setUrls(values);
        else values.forEach(URL.revokeObjectURL);
      })
      .catch(() => {
        if (active) { setUrls([]); setFailed(true); }
      });
    return () => {
      active = false;
      loaded.forEach(URL.revokeObjectURL);
    };
  }, [accessToken, post.id, post.images, fetchImage]);
  if (failed) return <Typography role="status">Não foi possível carregar as imagens.</Typography>;
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
            position: "relative",
            overflow: "hidden",
          }}
        >
          {onRemove && (
            <IconButton
              aria-label={`Remover imagem ${index + 1}`}
              onClick={(event) => {
                event.stopPropagation();
                onRemove(post.images[index].id);
              }}
              size="small"
              sx={{ bgcolor: "background.paper", position: "absolute", right: 6, top: 6, zIndex: 1 }}
            >
              <span aria-hidden="true">×</span>
            </IconButton>
          )}
          <Box
            alt={description ?? `Imagem ${index + 1} da publicação de ${post.author_name}`}
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
