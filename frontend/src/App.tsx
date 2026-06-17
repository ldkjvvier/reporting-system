import {
  AppShell,
  Badge,
  Burger,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  UnstyledButton,
} from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import {
  IconReportAnalytics,
  IconLogout,
  IconFileAnalytics,
  IconUsers,
  IconUsersGroup,
} from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ReportForm from "./pages/ReportForm";
import RunHistory from "./pages/RunHistory";
import AdminUsers from "./pages/AdminUsers";
import AdminTeams from "./pages/AdminTeams";
import type { ReactNode } from "react";

const ACCENT = "#60A5FA";

function Protected({ children }: { children: ReactNode }) {
  const { isAuthed, loading } = useAuth();
  if (loading)
    return (
      <Center mih="100vh">
        <Loader />
      </Center>
    );
  return isAuthed ? <>{children}</> : <Navigate to="/login" replace />;
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { isAdmin, loading } = useAuth();
  if (loading)
    return (
      <Center mih="100vh">
        <Loader />
      </Center>
    );
  return isAdmin ? <>{children}</> : <Navigate to="/" replace />;
}

function NavItem({
  icon: ItemIcon,
  label,
  active,
  onClick,
}: {
  icon: Icon;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <UnstyledButton className="nav-item" data-active={active} onClick={onClick}>
      <ItemIcon size={18} stroke={1.7} />
      <span>{label}</span>
    </UnstyledButton>
  );
}

function SidebarContent({ onNavigate }: { onNavigate: () => void }) {
  const { user, logout, isAdmin } = useAuth();
  const nav = useNavigate();
  const { pathname } = useLocation();

  const go = (to: string) => {
    nav(to);
    onNavigate();
  };

  const roleLabel = isAdmin
    ? "Administrador"
    : user?.memberships.some((m) => m.role === "editor")
    ? "Editor"
    : "Lector";

  const reportsActive = pathname === "/" || pathname.startsWith("/reports");

  return (
    <Stack h="100%" gap={0} p="md">
      {/* Marca */}
      <Group gap="sm" px={4} pb="lg" wrap="nowrap">
        <IconReportAnalytics size={26} color={ACCENT} />
        <div>
          <Text fw={600} c="white" size="sm" lh={1.2}>
            Reportería Automatizada
          </Text>
          <Text size="xs" c="blue.3" lh={1.2}>
            Datadog Cloud SIEM
          </Text>
        </div>
      </Group>

      {/* Navegación */}
      <Stack gap={4}>
        <NavItem
          icon={IconFileAnalytics}
          label="Reportes"
          active={reportsActive}
          onClick={() => go("/")}
        />

        {isAdmin && (
          <>
            <Text
              size="xs"
              fw={600}
              c="rgba(255,255,255,0.4)"
              tt="uppercase"
              mt="lg"
              mb={4}
              px={12}
              style={{ letterSpacing: "0.07em" }}
            >
              Administración
            </Text>
            <NavItem
              icon={IconUsers}
              label="Usuarios"
              active={pathname === "/admin/users"}
              onClick={() => go("/admin/users")}
            />
            <NavItem
              icon={IconUsersGroup}
              label="Equipos"
              active={pathname === "/admin/teams"}
              onClick={() => go("/admin/teams")}
            />
          </>
        )}
      </Stack>

      {/* Usuario + salir (al fondo) */}
      <Stack gap="xs" mt="auto" pt="md">
        <Group
          gap="xs"
          px={12}
          py={8}
          wrap="nowrap"
          style={{
            borderRadius: 8,
            backgroundColor: "rgba(255,255,255,0.04)",
          }}
        >
          <Stack gap={2} style={{ minWidth: 0, flex: 1 }}>
            <Text c="white" size="sm" fw={500} truncate>
              {user?.email}
            </Text>
            <Badge
              size="xs"
              variant="light"
              color={isAdmin ? "orange" : "blue"}
              radius="sm"
            >
              {roleLabel}
            </Badge>
          </Stack>
        </Group>
        <UnstyledButton
          className="nav-item"
          onClick={() => {
            logout();
            nav("/login");
          }}
        >
          <IconLogout size={18} stroke={1.7} />
          <span>Cerrar sesión</span>
        </UnstyledButton>
      </Stack>
    </Stack>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const [opened, { toggle, close }] = useDisclosure(false);
  // La cabecera superior es solo para móvil; en escritorio se colapsa para no
  // reservar espacio vacío encima del contenido.
  const isDesktop = useMediaQuery("(min-width: 48em)", true);

  return (
    <AppShell
      header={{ height: 56, collapsed: isDesktop }}
      navbar={{ width: 264, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="lg"
      bg="gray.0"
    >
      {/* Cabecera solo en móvil: marca + botón de menú */}
      <AppShell.Header
        hiddenFrom="sm"
        style={{ backgroundColor: "#0D1F35", borderBottom: "1px solid #1a3355" }}
      >
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <IconReportAnalytics size={20} color={ACCENT} />
            <Text fw={600} c="white" size="sm">
              Reportería
            </Text>
          </Group>
          <Burger opened={opened} onClick={toggle} color="white" size="sm" />
        </Group>
      </AppShell.Header>

      <AppShell.Navbar className="app-sidebar" style={{ border: "none" }}>
        <SidebarContent onNavigate={close} />
      </AppShell.Navbar>

      <AppShell.Main>{children}</AppShell.Main>
    </AppShell>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Shell>
              <Dashboard />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/reports/new"
        element={
          <Protected>
            <Shell>
              <ReportForm />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/reports/:id/edit"
        element={
          <Protected>
            <Shell>
              <ReportForm />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/reports/:id/runs"
        element={
          <Protected>
            <Shell>
              <RunHistory />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/admin/users"
        element={
          <Protected>
            <AdminOnly>
              <Shell>
                <AdminUsers />
              </Shell>
            </AdminOnly>
          </Protected>
        }
      />
      <Route
        path="/admin/teams"
        element={
          <Protected>
            <AdminOnly>
              <Shell>
                <AdminTeams />
              </Shell>
            </AdminOnly>
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
