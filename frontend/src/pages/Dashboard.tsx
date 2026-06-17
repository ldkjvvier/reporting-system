import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import {
  IconPlayerPlay,
  IconPencil,
  IconTrash,
  IconHistory,
  IconPlus,
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { adminApi, apiError, reportsApi } from "../api";
import { useAuth } from "../auth";
import type { Report, Team } from "../types";

// Etiqueta y color del badge según la fuente Datadog del reporte.
const SOURCE_BADGE: Record<Report["source_type"], [string, string]> = {
  signals: ["Security Signals", "red"],
  logs: ["Logs", "blue"],
  metrics: ["Métricas", "teal"],
};

function cronHumano(cron: string): string {
  const presets: Record<string, string> = {
    "0 8 * * *": "Diario 08:00",
    "0 8 * * 1": "Lunes 08:00",
    "0 8 1 * *": "Mensual día 1, 08:00",
    "*/5 * * * *": "Cada 5 min",
    "* * * * *": "Cada minuto",
  };
  return presets[cron] || cron;
}

export default function Dashboard() {
  const nav = useNavigate();
  const { user, isAdmin, canEdit } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);

  // Nombre de equipo: admins cargan todos; miembros lo derivan de sus membresías.
  const teamName = useMemo(() => {
    const map = new Map<number, string>();
    teams.forEach((t) => map.set(t.id, t.name));
    user?.memberships.forEach((m) => map.set(m.team_id, m.team_name));
    return (id: number) => map.get(id) ?? `Equipo ${id}`;
  }, [teams, user]);

  const load = async () => {
    setLoading(true);
    try {
      setReports(await reportsApi.list());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    if (isAdmin) adminApi.listTeams().then(setTeams).catch(() => {});
  }, [isAdmin]);

  const runNow = async (r: Report) => {
    try {
      await reportsApi.runNow(r.id);
      notifications.show({
        color: "blue",
        title: "Ejecución encolada",
        message: `'${r.name}' se está generando. Revisa el historial.`,
      });
    } catch (e: any) {
      notifications.show({ color: "red", message: apiError(e, "No se pudo ejecutar el reporte") });
    }
  };

  const remove = async (r: Report) => {
    if (!confirm(`¿Eliminar el reporte "${r.name}"?`)) return;
    try {
      await reportsApi.remove(r.id);
      notifications.show({ color: "gray", message: "Reporte eliminado" });
      load();
    } catch (e: any) {
      notifications.show({ color: "red", message: apiError(e, "No se pudo eliminar el reporte") });
    }
  };

  const canCreate =
    isAdmin || (user?.memberships.some((m) => m.role === "editor") ?? false);

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>{isAdmin ? "Todos los reportes" : "Reportes"}</Title>
          <Text c="dimmed">
            Reportes automáticos sobre Datadog Cloud SIEM
          </Text>
        </div>
        {canCreate && (
          <Button
            leftSection={<IconPlus size={16} />}
            onClick={() => nav("/reports/new")}
          >
            Nuevo reporte
          </Button>
        )}
      </Group>

      <Card withBorder padding="lg" radius="md">
        {reports.length === 0 && !loading ? (
          <Text c="dimmed" ta="center" py="xl">
            Aún no tienes reportes. Crea el primero con “Nuevo reporte”.
          </Text>
        ) : (
          <Table highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Nombre</Table.Th>
                <Table.Th>Equipo</Table.Th>
                <Table.Th>Fuente</Table.Th>
                <Table.Th>Formato</Table.Th>
                <Table.Th>Programación</Table.Th>
                <Table.Th>Próxima ejecución</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th ta="right">Acciones</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {reports.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>
                    <Text fw={500}>{r.name}</Text>
                    <Text size="xs" c="dimmed">
                      {r.recipients.length} destinatario(s)
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline" color="grape">
                      {teamName(r.team_id)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="light" color={SOURCE_BADGE[r.source_type][1]}>
                      {SOURCE_BADGE[r.source_type][0]}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{r.output_format.toUpperCase()}</Table.Td>
                  <Table.Td>{cronHumano(r.cron)}</Table.Td>
                  <Table.Td>
                    {r.next_run
                      ? new Date(r.next_run).toLocaleString()
                      : "—"}
                  </Table.Td>
                  <Table.Td>
                    <Badge color={r.enabled ? "green" : "gray"} variant="dot">
                      {r.enabled ? "Activo" : "Pausado"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} justify="flex-end">
                      {canEdit(r.team_id) && (
                        <Tooltip label="Ejecutar ahora">
                          <ActionIcon variant="subtle" color="green" onClick={() => runNow(r)}>
                            <IconPlayerPlay size={18} />
                          </ActionIcon>
                        </Tooltip>
                      )}
                      <Tooltip label="Historial">
                        <ActionIcon
                          variant="subtle"
                          onClick={() => nav(`/reports/${r.id}/runs`)}
                        >
                          <IconHistory size={18} />
                        </ActionIcon>
                      </Tooltip>
                      {canEdit(r.team_id) && (
                        <>
                          <Tooltip label="Editar">
                            <ActionIcon
                              variant="subtle"
                              color="blue"
                              onClick={() => nav(`/reports/${r.id}/edit`)}
                            >
                              <IconPencil size={18} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Eliminar">
                            <ActionIcon variant="subtle" color="red" onClick={() => remove(r)}>
                              <IconTrash size={18} />
                            </ActionIcon>
                          </Tooltip>
                        </>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
