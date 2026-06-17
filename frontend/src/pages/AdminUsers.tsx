import {
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Modal,
  PasswordInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconPencil } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { adminApi, apiError, type MembershipInput } from "../api";
import type { Team, TeamRole, User } from "../types";

const ROLE_OPTIONS = [
  { value: "none", label: "Sin acceso" },
  { value: "editor", label: "Editor" },
  { value: "viewer", label: "Viewer" },
];

interface FormState {
  email: string;
  password: string;
  is_admin: boolean;
  roles: Record<number, TeamRole | "none">; // team_id -> rol
}

const emptyForm = (): FormState => ({
  email: "",
  password: "",
  is_admin: false,
  roles: {},
});

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [opened, setOpened] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [saving, setSaving] = useState(false);

  const load = () => {
    adminApi.listUsers().then(setUsers);
    adminApi.listTeams().then(setTeams);
  };

  useEffect(() => {
    load();
  }, []);

  const toMemberships = (roles: FormState["roles"]): MembershipInput[] =>
    Object.entries(roles)
      .filter(([, role]) => role !== "none")
      .map(([team_id, role]) => ({ team_id: Number(team_id), role: role as TeamRole }));

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setOpened(true);
  };

  const openEdit = (u: User) => {
    setEditingId(u.id);
    const roles: FormState["roles"] = {};
    u.memberships.forEach((m) => (roles[m.team_id] = m.role));
    setForm({ email: u.email, password: "", is_admin: u.is_admin, roles });
    setOpened(true);
  };

  const submit = async () => {
    setSaving(true);
    try {
      const memberships = toMemberships(form.roles);
      if (editingId === null) {
        await adminApi.createUser({
          email: form.email,
          password: form.password,
          is_admin: form.is_admin,
          memberships,
        });
        notifications.show({ color: "green", message: "Usuario creado" });
      } else {
        await adminApi.updateUser(editingId, {
          is_admin: form.is_admin,
          memberships,
          ...(form.password ? { password: form.password } : {}),
        });
        notifications.show({ color: "green", message: "Usuario actualizado" });
      }
      setOpened(false);
      load();
    } catch (e: any) {
      notifications.show({
        color: "red",
        title: "Error",
        message: apiError(e, "No se pudo guardar el usuario"),
      });
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (u: User) => {
    if (u.is_active) {
      if (!confirm(`¿Desactivar la cuenta de ${u.email}?`)) return;
      await adminApi.deactivateUser(u.id);
    } else {
      await adminApi.updateUser(u.id, { is_active: true });
    }
    load();
  };

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Usuarios</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={openCreate}>
          Nuevo usuario
        </Button>
      </Group>

      <Card withBorder padding="lg" radius="md">
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Correo</Table.Th>
              <Table.Th>Rol global</Table.Th>
              <Table.Th>Equipos</Table.Th>
              <Table.Th>Estado</Table.Th>
              <Table.Th ta="right">Acciones</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.map((u) => (
              <Table.Tr key={u.id}>
                <Table.Td>{u.email}</Table.Td>
                <Table.Td>
                  {u.is_admin ? (
                    <Badge color="orange">Admin</Badge>
                  ) : (
                    <Text size="sm" c="dimmed">
                      —
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    {u.memberships.length === 0 && u.is_admin && (
                      <Text size="xs" c="dimmed">
                        (todos)
                      </Text>
                    )}
                    {u.memberships.map((m) => (
                      <Badge
                        key={m.team_id}
                        variant="light"
                        color={m.role === "editor" ? "blue" : "gray"}
                      >
                        {m.team_name}: {m.role}
                      </Badge>
                    ))}
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Badge color={u.is_active ? "green" : "red"} variant="dot">
                    {u.is_active ? "Activo" : "Inactivo"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    <Button
                      size="xs"
                      variant="subtle"
                      leftSection={<IconPencil size={14} />}
                      onClick={() => openEdit(u)}
                    >
                      Editar
                    </Button>
                    <Button
                      size="xs"
                      variant="subtle"
                      color={u.is_active ? "red" : "green"}
                      onClick={() => toggleActive(u)}
                    >
                      {u.is_active ? "Desactivar" : "Activar"}
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={editingId === null ? "Nuevo usuario" : "Editar usuario"}
        size="lg"
      >
        <Stack>
          <TextInput
            label="Correo"
            required
            value={form.email}
            disabled={editingId !== null}
            onChange={(e) => {
              const value = e.currentTarget.value;
              setForm((f) => ({ ...f, email: value }));
            }}
          />
          <PasswordInput
            label={editingId === null ? "Contraseña" : "Nueva contraseña (opcional)"}
            required={editingId === null}
            value={form.password}
            onChange={(e) => {
              const value = e.currentTarget.value;
              setForm((f) => ({ ...f, password: value }));
            }}
          />
          <Checkbox
            label="Administrador global (acceso a todos los equipos)"
            checked={form.is_admin}
            onChange={(e) => {
              const checked = e.currentTarget.checked;
              setForm((f) => ({ ...f, is_admin: checked }));
            }}
          />

          <div>
            <Text fw={500} size="sm" mb={4}>
              Acceso por equipo
            </Text>
            <Text size="xs" c="dimmed" mb="xs">
              Los administradores ven todos los equipos aunque no se asignen aquí.
            </Text>
            <Stack gap="xs">
              {teams.length === 0 && (
                <Text size="sm" c="dimmed">
                  No hay equipos creados todavía.
                </Text>
              )}
              {teams.map((t) => (
                <Group key={t.id} justify="space-between">
                  <Text size="sm">{t.name}</Text>
                  <Select
                    w={160}
                    data={ROLE_OPTIONS}
                    value={form.roles[t.id] ?? "none"}
                    onChange={(v) =>
                      setForm((f) => ({
                        ...f,
                        roles: { ...f.roles, [t.id]: (v as TeamRole | "none") ?? "none" },
                      }))
                    }
                  />
                </Group>
              ))}
            </Stack>
          </div>

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>
              Cancelar
            </Button>
            <Button
              loading={saving}
              onClick={submit}
              disabled={!form.email || (editingId === null && !form.password)}
            >
              Guardar
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
