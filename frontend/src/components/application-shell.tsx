import {
  AppBar,
  Avatar,
  Box,
  Button,
  Container,
  Drawer,
  IconButton,
  Stack,
  Toolbar,
  ThemeProvider,
  Typography,
} from "@mui/material";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { OidcSessionClient } from "../auth";
import { getOccupancy } from "../occupancy";
import { fetchProfileImage, getOwnSocialProfile } from "../social";
import { RouterButtonLink } from "./router-button-link";
import { WorkspaceIcon, WorkspacePresentationContext, workspaceTheme, navigationLinkSx, type WorkspaceIconName } from "./workspace-presentation";
import { AreaSwitch, type ApplicationArea } from "./area-switch";
type ShellProps = { children: ReactNode; onSignOut?: () => void };
type ContentMaxWidth = false | "xs" | "sm" | "md" | "lg" | "xl";

const OnboardingNavigationContext = createContext<boolean | null>(null);

export function ClientNavigationStateProvider({
  children,
  onboardingComplete,
}: {
  children: ReactNode;
  onboardingComplete: boolean | null;
}) {
  return (
    <OnboardingNavigationContext.Provider value={onboardingComplete}>
      {children}
    </OnboardingNavigationContext.Provider>
  );
}

function Brand({ heading = false }: { heading?: boolean }) {
  return (
    <Stack direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
      <Box
        aria-hidden="true"
        sx={{
          bgcolor: "primary.main",
          borderRadius: 1,
          height: 18,
          transform: "skewX(-18deg)",
          width: 7,
        }}
      />
      <Typography
        component={heading ? "h1" : "span"}
        sx={{ fontWeight: 850, letterSpacing: "-0.04em" }}
      >
        Academia Inteligente
      </Typography>
    </Stack>
  );
}

function ClientNavigation({
  compact = false,
  id,
  onNavigate,
}: {
  compact?: boolean;
  id?: string;
  onNavigate?: () => void;
}) {
  const currentPath = window.location.pathname;
  const onboardingComplete = useContext(OnboardingNavigationContext);
  const links: { href: string; label: string; icon: WorkspaceIconName }[] = [
    ...(onboardingComplete === false
      ? [{ href: "/onboarding", label: "Onboarding", icon: "onboarding" as const }]
      : []),
    { href: "/treino", label: "Meu treino", icon: "training" },
    { href: "/assistente", label: "Assistente", icon: "assistant" },
    { href: "/feed", label: "Feed", icon: "feed" },
    { href: "/equipamentos", label: "Equipamentos", icon: "equipment" },
  ];
  return (
    <Box
      component="nav"
      aria-label="Navegação da área do cliente"
      id={id}
      sx={
        compact
          ? { width: "100%" }
          : { borderTop: "1px solid", borderColor: "divider" }
      }
    >
      <Container
        disableGutters={compact}
        maxWidth={compact ? false : "lg"}
        sx={compact ? undefined : { px: { xs: 2, sm: 3 }, py: 1 }}
      >
        <Stack
          direction={compact ? "column" : "row"}
          spacing={compact ? 0.5 : 0.5}
          sx={compact ? { width: "100%" } : { flexWrap: "wrap", rowGap: 0.5 }}
          useFlexGap
        >
          {links.map((link) => {
            const active =
              currentPath === link.href ||
              (link.href === "/" && currentPath === "/dashboard");
            return (
              <RouterButtonLink
                startIcon={<WorkspaceIcon name={link.icon} />}
                aria-current={active ? "page" : undefined}
                color={active ? "primary" : "inherit"}
                key={link.href}
                onClick={onNavigate}
                size={compact ? "medium" : "small"}
                sx={compact ? navigationLinkSx : undefined}
                to={link.href}
                variant="text"
              >
                {link.label}
              </RouterButtonLink>
            );
          })}
        </Stack>
      </Container>
    </Box>
  );
}

function OccupancyIndicator({ count }: { count: number | null }) {
  const label = count === null
    ? "Ocupação da academia indisponível"
    : count === 1
      ? "1 pessoa na academia"
      : `${count} pessoas na academia`;
  return (
    <Box aria-label={label} role="status" sx={{ alignItems: "center", display: "flex", gap: 1, px: 1.5, py: 1, borderRadius: 2, bgcolor: "action.hover", color: "text.secondary" }}>
      <WorkspaceIcon name="clients" />
      <Typography component="span" sx={{ fontWeight: 700 }}>
        {count ?? "—"}
      </Typography>
      <Typography variant="caption">na academia</Typography>
    </Box>
  );
}

function ProfileNavigationLink({
  imageUrl,
  name,
  onNavigate,
}: {
  imageUrl: string | null;
  name: string;
  onNavigate?: () => void;
}) {
  return (
    <RouterButtonLink
      aria-label="Abrir meu perfil"
      onClick={onNavigate}
      sx={{ justifyContent: "flex-start", px: 1.5, py: 1, width: "100%" }}
      to="/perfil"
      variant="text"
    >
      <Avatar alt={`Foto de ${name}`} src={imageUrl ?? undefined} sx={{ height: 28, mr: 1, width: 28 }}>
        {name.slice(0, 1)}
      </Avatar>
      <Typography component="span" noWrap sx={{ maxWidth: 150, overflow: "hidden", textOverflow: "ellipsis" }}>
        {name}
      </Typography>
    </RouterButtonLink>
  );
}

function SignOutButton({
  onSignOut,
  fullWidth = false,
}: {
  onSignOut?: () => void;
  fullWidth?: boolean;
}) {
  const [signingOut, setSigningOut] = useState(false);

  function signOut() {
    if (!onSignOut || signingOut) return;
    setSigningOut(true);
    onSignOut();
  }

  if (!onSignOut) return null;
  return (
    <Button
      startIcon={fullWidth ? <WorkspaceIcon name="logout" /> : undefined}
      color="inherit"
      disabled={signingOut}
      onClick={signOut}
      sx={
        fullWidth
          ? { justifyContent: "flex-start", px: 1.5, width: "100%" }
          : undefined
      }
    >
      {signingOut ? "Saindo…" : "Sair"}
    </Button>
  );
}

function BaseShell({
  children,
  onSignOut,
  area,
  navigation,
  contentMaxWidth = "lg",
}: ShellProps & {
  area: string;
  navigation?: ReactNode;
  contentMaxWidth?: ContentMaxWidth;
}) {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "linear-gradient(160deg, #10181B 0%, #162427 52%, #10181B 100%)",
      }}
    >
      <AppBar
        color="transparent"
        elevation={0}
        position="sticky"
        sx={{
          backdropFilter: "blur(14px)",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Toolbar
          sx={{ gap: 2, minHeight: { xs: 64, sm: 72 }, px: { xs: 2, sm: 3 } }}
        >
          <Brand />
          <Typography
            color="text.secondary"
            sx={{
              display: { xs: "none", sm: "block" },
              fontSize: "0.875rem",
              ml: 1,
            }}
          >
            {area}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <SignOutButton onSignOut={onSignOut} />
        </Toolbar>
        {navigation}
      </AppBar>
      <Container
        component="main"
        maxWidth={contentMaxWidth}
        sx={{ py: { xs: 3, sm: 5 } }}
      >
        {children}
      </Container>
    </Box>
  );
}

function ClientNavigationShell({
  children,
  contentMaxWidth = "lg",
  onSignOut,
}: ShellProps & { contentMaxWidth?: ContentMaxWidth }) {
  const [profileName, setProfileName] = useState("Meu perfil");
  const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
  const [occupancy, setOccupancy] = useState<number | null>(null);

  useEffect(() => {
    const accessToken = new OidcSessionClient().getSession()?.accessToken;
    if (!accessToken) return;
    let active = true;
    let imageUrl: string | null = null;
    void getOwnSocialProfile(accessToken)
      .then(async (profile) => {
        if (!active) return;
        const name = profile.nickname || profile.name;
        if (typeof name === "string" && name) setProfileName(name);
        if (!profile.has_image) return;
        imageUrl = await fetchProfileImage(accessToken, profile.id);
        if (active) setProfileImageUrl(imageUrl);
        else URL.revokeObjectURL(imageUrl);
      })
      .catch(() => undefined);
    return () => {
      active = false;
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, []);

  useEffect(() => {
    let active = true;
    const load = () => {
      void getOccupancy()
        .then((value) => {
          if (active && Number.isFinite(value.occupancy)) setOccupancy(value.occupancy);
        })
        .catch(() => undefined);
    };
    load();
    const refresh = window.setInterval(load, 60_000);
    return () => {
      active = false;
      window.clearInterval(refresh);
    };
  }, []);

  return (
    <SidebarShell
      area="client"
      contentMaxWidth={contentMaxWidth}
      navigationId="navegacao-cliente-movel"
      onSignOut={onSignOut}
      renderNavigation={({ id, onNavigate }) => (
        <ClientNavigation compact id={id} onNavigate={onNavigate} />
      )}
      renderFooter={(onNavigate) => (
        <>
          <Box sx={{ mb: 1.5 }}><OccupancyIndicator count={occupancy} /></Box>
          <ProfileNavigationLink imageUrl={profileImageUrl} name={profileName} onNavigate={onNavigate} />
        </>
      )}
    >
      {children}
    </SidebarShell>
  );
}

/** Shared responsive layout only; each area supplies its own authorized navigation. */
export function SidebarShell({
  area,
  children,
  contentMaxWidth = "lg",
  navigationId,
  onSignOut,
  renderNavigation,
  renderFooter,
}: ShellProps & {
  area: ApplicationArea;
  contentMaxWidth?: ContentMaxWidth;
  navigationId: string;
  renderNavigation: (options: { id?: string; onNavigate?: () => void }) => ReactNode;
  renderFooter?: (onNavigate?: () => void) => ReactNode;
}) {
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  return (
    <ThemeProvider theme={workspaceTheme}><WorkspacePresentationContext.Provider value={true}>
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "radial-gradient(ellipse at top right, #1B2B2D 0%, #10181B 65%)",
      }}
    >
      <Box
        sx={{
          display: { md: "none" },
          position: "sticky",
          top: 0,
          zIndex: "appBar",
          bgcolor: "background.default",
          backdropFilter: "blur(14px)",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Toolbar sx={{ gap: 2, minHeight: 64, px: 2 }}>
          <IconButton
            aria-controls={navigationId}
            aria-expanded={mobileNavigationOpen}
            aria-label="Abrir navegação"
            onClick={() => setMobileNavigationOpen(true)}
          >
            <WorkspaceIcon name="menu" />
          </IconButton>
          <Brand />
          <Box sx={{ flexGrow: 1 }} />
        </Toolbar>
      </Box>
      <Drawer
        anchor="left"
        onClose={() => setMobileNavigationOpen(false)}
        open={mobileNavigationOpen}
        sx={{ display: { md: "none" } }}
      >
        <Box
          component="aside"
          sx={{
            background:
              "linear-gradient(160deg, #10181B 0%, #162427 52%, #10181B 100%)",
            display: "flex",
            flexDirection: "column",
            minHeight: "100%",
            p: 2,
            width: "min(90vw, 320px)",
          }}
        >
          <Stack
            direction="row"
            sx={{ alignItems: "center", justifyContent: "space-between", px: 1.5, py: 1.25 }}
          >
            <Brand />
            <IconButton aria-label="Fechar navegação" onClick={() => setMobileNavigationOpen(false)}>
              <WorkspaceIcon name="close" />
            </IconButton>
          </Stack>
          <Box sx={{ mt: 4 }}>
            <Typography variant="overline" color="text.secondary" sx={{ display: "block", px: 1.75, mb: 1.5 }}>{area === "client" ? "Área do cliente" : "Área do instrutor"}</Typography>
            {renderNavigation({ id: navigationId, onNavigate: () => setMobileNavigationOpen(false) })}
          </Box>
          <Box sx={{ mt: "auto", pt: 3, pb: 1 }}>
            <AreaSwitch area={area} onNavigate={() => setMobileNavigationOpen(false)} />
            {renderFooter?.(() => setMobileNavigationOpen(false))}
            <SignOutButton fullWidth onSignOut={onSignOut} />
          </Box>
        </Box>
      </Drawer>
      <Box
        sx={{
          display: { md: "grid" },
          gridTemplateColumns: { md: "256px minmax(0, 1fr)" },
          minHeight: "100vh",
        }}
      >
        <Box
          component="aside"
          sx={{
            bgcolor: "#111C20",
            borderRight: "1px solid",
            borderColor: "divider",
            display: { xs: "none", md: "flex" },
            flexDirection: "column",
            minHeight: 0,
            overflowY: "auto",
            p: 2,
            position: "sticky",
            top: 0,
            height: "100dvh",
          }}
        >
          <Box sx={{ px: 1.5, py: 1.25 }}>
            <Brand />
          </Box>
          <Box sx={{ mt: 4 }}>
            <Typography variant="overline" color="text.secondary" sx={{ display: "block", px: 1.75, mb: 1.5 }}>{area === "client" ? "Área do cliente" : "Área do instrutor"}</Typography>
            {renderNavigation({})}
          </Box>
          <Box sx={{ mt: "auto", pt: 3, pb: 1 }}>
            <AreaSwitch area={area} />
            {renderFooter?.()}
            <SignOutButton fullWidth onSignOut={onSignOut} />
          </Box>
        </Box>
        <Container
          component="main"
          maxWidth={contentMaxWidth}
          sx={{
            minWidth: 0,
            py: { xs: 3, sm: 4, md: 5 },
            px: { xs: 2, sm: 3, lg: 4 },
          }}
        >
          {children}
        </Container>
      </Box>
    </Box>
    </WorkspacePresentationContext.Provider></ThemeProvider>
  );
}

export function PublicShell({ children, contentMaxWidth = "md" }: { children: ReactNode; contentMaxWidth?: ContentMaxWidth }) {
  return (
    <Box
      component="main"
      sx={{
        background:
          "linear-gradient(145deg, #10181B 0%, #1B2A2E 58%, #10181B 100%)",
        minHeight: "100vh",
      }}
    >
      <Container maxWidth={contentMaxWidth} sx={{ py: { xs: 3, sm: 5 } }}>
        <Box component="header" sx={{ mb: { xs: 6, sm: 10 } }}>
          <Brand heading />
        </Box>
        {children}
      </Container>
    </Box>
  );
}

export function AdminShell({ children, onSignOut }: ShellProps) {
  return (
    <BaseShell area="Administração" onSignOut={onSignOut}>
      {children}
    </BaseShell>
  );
}

export function ClientShell({
  children,
  onSignOut,
  showClientNavigation = false,
  contentMaxWidth,
}: ShellProps & {
  showClientNavigation?: boolean;
  contentMaxWidth?: ContentMaxWidth;
}) {
  if (showClientNavigation)
    return (
      <ClientNavigationShell
        contentMaxWidth={contentMaxWidth}
        onSignOut={onSignOut}
      >
        {children}
      </ClientNavigationShell>
    );
  return (
    <BaseShell
      area="Área do cliente"
      contentMaxWidth={contentMaxWidth}
      onSignOut={onSignOut}
    >
      {children}
    </BaseShell>
  );
}
