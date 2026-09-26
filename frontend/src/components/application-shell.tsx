import {
  AppBar,
  Box,
  Button,
  Container,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { createContext, useContext, useState, type ReactNode } from "react";

import { RouterButtonLink } from "./router-button-link";
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

function ClientNavigation({ compact = false }: { compact?: boolean }) {
  const currentPath = window.location.pathname;
  const onboardingComplete = useContext(OnboardingNavigationContext);
  const links = [
    { href: "/", label: "Início" },
    ...(onboardingComplete === false
      ? [{ href: "/onboarding", label: "Onboarding" }]
      : []),
    { href: "/treino", label: "Meu treino" },
    { href: "/assistente", label: "Assistente" },
    { href: "/feed", label: "Feed" },
    { href: "/equipamentos", label: "Equipamentos" },
    { href: "/ocupacao", label: "Ocupação" },
    { href: "/perfil", label: "Meu perfil" },
  ];
  return (
    <Box
      component="nav"
      aria-label="Navegação da área do cliente"
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
                aria-current={active ? "page" : undefined}
                color={active ? "primary" : "inherit"}
                key={link.href}
                size={compact ? "medium" : "small"}
                sx={
                  compact
                    ? {
                        justifyContent: "flex-start",
                        px: 1.5,
                        py: 1,
                        width: "100%",
                      }
                    : undefined
                }
                to={link.href}
                variant={active ? "contained" : "text"}
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
  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "linear-gradient(160deg, #10181B 0%, #162427 52%, #10181B 100%)",
      }}
    >
      <Box
        sx={{
          display: { md: "none" },
          position: "sticky",
          top: 0,
          zIndex: "appBar",
          backdropFilter: "blur(14px)",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Toolbar sx={{ gap: 2, minHeight: 64, px: 2 }}>
          <Brand />
          <Box sx={{ flexGrow: 1 }} />
          <SignOutButton onSignOut={onSignOut} />
        </Toolbar>
        <ClientNavigation />
      </Box>
      <Box
        sx={{
          display: { md: "grid" },
          gridTemplateColumns: { md: "248px minmax(0, 1fr)" },
          minHeight: "100vh",
        }}
      >
        <Box
          component="aside"
          sx={{
            borderRight: "1px solid",
            borderColor: "divider",
            display: { xs: "none", md: "flex" },
            flexDirection: "column",
            minHeight: "100vh",
            p: 2,
            position: "sticky",
            top: 0,
            height: "100vh",
          }}
        >
          <Box sx={{ px: 1.5, py: 1.25 }}>
            <Brand />
          </Box>
          <Box sx={{ mt: 3 }}>
            <ClientNavigation compact />
          </Box>
          <Box sx={{ mt: "auto", pb: 1 }}>
            <SignOutButton fullWidth onSignOut={onSignOut} />
          </Box>
        </Box>
        <Container
          component="main"
          maxWidth={contentMaxWidth}
          sx={{
            minWidth: 0,
            py: { xs: 3, sm: 4, md: 5 },
            px: { xs: 2, sm: 3 },
          }}
        >
          {children}
        </Container>
      </Box>
    </Box>
  );
}

export function PublicShell({ children }: { children: ReactNode }) {
  return (
    <Box
      component="main"
      sx={{
        background:
          "linear-gradient(145deg, #10181B 0%, #1B2A2E 58%, #10181B 100%)",
        minHeight: "100vh",
      }}
    >
      <Container maxWidth="md" sx={{ py: { xs: 3, sm: 5 } }}>
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
