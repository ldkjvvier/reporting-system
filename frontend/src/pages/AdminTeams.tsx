import {
  ActionIcon,
  Button,
  Card,
  Group,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconTrash, IconDeviceFloppy, IconPlus } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { adminApi } from "../api";
import type { Team } from "../types";

export default function AdminTeams() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [newName, setNewName] = useState("");
  const [edited, setEdited] = useState<Record<number, string>>({});

  const load = () => adminApi.listTeams().then(setTeams);

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!newName.trim()) return;
    try {
      await adminApi.createTeam(newName.trim());
      setNewName("");
      notifications.show({ color: "green", message: "Equipo creado" });
      load();
    } catch (e: any) {
      notifications.show({
        color: "red",
        message: e?.response?.data?.detail || "No se pudo crear el equipo",
      });
    }
  };

  const rename = async (t: Team) => {
    const name = (edited[t.id] ?? t.name).trim();
    if (!name || name === t.name) return;
    try {
      await adminApi.updateTeam(t.id, name);
      notifications.show({ color: "green", message: "Equipo actualizado" });
      load();
    } catch (e: any) {
      notifications.show({
        color: "red",
        message: e?.response?.data?.detail || "No se pudo actualizar",
      });
    }
  };

  const remove = async (t: Team) => {
    if (!confirm(`¿Eliminar el equipo "${t.name}"?`)) return;
    try {
      await adminApi.deleteTeam(t.id);
      notifications.show({ color: "gray", message: "Equipo eliminado" });
      load();
    } catch (e: any) {
      notifications.show({
        color: "red",
        message: e?.response?.data?.detail || "No se pudo eliminar",
      });
    }
  };

  return (
    <Stack>
      <Title order={2}>Equipos</Title>

      <Card withBorder padding="lg" radius="md">
        <Group align="flex-end">
          <TextInput
            label="Nuevo equipo"
            placeholder="Nombre del equipo"
            value={newName}
            onChange={(e) => setNewName(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && create()}
            style={{ flex: 1 }}
          />
          <Button leftSection={<IconPlus size={16} />} onClick={create}>
            Crear
          </Button>
        </Group>
      </Card>

      <Card withBorder padding="lg" radius="md">
        {teams.length === 0 ? (
          <Text c="dimmed" ta="center" py="md">
            Aún no hay equipos.
          </Text>
        ) : (
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Nombre</Table.Th>
                <Table.Th ta="right">Acciones</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {teams.map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td>
                    <TextInput
                      value={edited[t.id] ?? t.name}
                      onChange={(e) => {
                        const value = e.currentTarget.value;
                        setEdited((s) => ({ ...s, [t.id]: value }));
                      }}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} justify="flex-end">
                      <Tooltip label="Guardar nombre">
                        <ActionIcon variant="subtle" color="blue" onClick={() => rename(t)}>
                          <IconDeviceFloppy size={18} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Eliminar">
                        <ActionIcon variant="subtle" color="red" onClick={() => remove(t)}>
                          <IconTrash size={18} />
                        </ActionIcon>
                      </Tooltip>
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
