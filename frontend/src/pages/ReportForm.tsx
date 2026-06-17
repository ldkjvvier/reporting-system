import {
  Button,
  Card,
  Checkbox,
  Group,
  MultiSelect,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Stepper,
  Table,
  TagsInput,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { adminApi, apiError, datadogApi, reportsApi } from "../api";
import { useAuth } from "../auth";
import type { PreviewResponse, ReportInput, Team } from "../types";

const WINDOWS = [
  { value: "last_1h", label: "Última hora" },
  { value: "last_24h", label: "Últimas 24 horas" },
  { value: "last_7d", label: "Últimos 7 días" },
  { value: "last_30d", label: "Últimos 30 días" },
];

const CRON_PRESETS = [
  { value: "0 8 * * *", label: "Diario a las 08:00" },
  { value: "0 8 * * 1", label: "Semanal (lunes 08:00)" },
  { value: "0 8 1 * *", label: "Mensual (día 1, 08:00)" },
  { value: "*/5 * * * *", label: "Cada 5 minutos (pruebas)" },
  { value: "* * * * *", label: "Cada minuto (pruebas)" },
  { value: "custom", label: "Personalizado…" },
];

// La programación se ejecuta en horario local de Chile (ver backend SCHEDULER_TIMEZONE).
const SCHEDULER_TZ = "America/Santiago";

const empty: ReportInput = {
  name: "",
  description: "",
  team_id: 0,
  source_type: "signals",
  query: "*",
  time_window: "last_24h",
  columns: [],
  output_format: "csv",
  recipients: [],
  cron: "0 8 * * *",
  timezone: SCHEDULER_TZ,
  enabled: true,
};

export default function ReportForm() {
  const { id } = useParams();
  const editing = !!id;
  const nav = useNavigate();
  const { user, isAdmin } = useAuth();

  const [active, setActive] = useState(0);
  const [form, setForm] = useState<ReportInput>(empty);
  const [fields, setFields] = useState<string[]>([]);
  const [allTeams, setAllTeams] = useState<Team[]>([]);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [cronPreset, setCronPreset] = useState<string>("0 8 * * *");

  const set = (patch: Partial<ReportInput>) => setForm((f) => ({ ...f, ...patch }));

  // Equipos donde el usuario puede crear/editar: todos si es admin, o aquellos
  // en los que tiene rol 'editor'.
  const editableTeams = useMemo(() => {
    if (isAdmin) return allTeams.map((t) => ({ value: String(t.id), label: t.name }));
    return (user?.memberships ?? [])
      .filter((m) => m.role === "editor")
      .map((m) => ({ value: String(m.team_id), label: m.team_name }));
  }, [isAdmin, allTeams, user]);

  useEffect(() => {
    if (isAdmin) adminApi.listTeams().then(setAllTeams).catch(() => {});
  }, [isAdmin]);

  // Preselecciona el único equipo editable al crear un reporte nuevo.
  useEffect(() => {
    if (!editing && form.team_id === 0 && editableTeams.length === 1) {
      set({ team_id: Number(editableTeams[0].value) });
    }
  }, [editing, editableTeams, form.team_id]);

  useEffect(() => {
    if (editing) {
      reportsApi.get(Number(id)).then((r) => {
        const { id: _i, created_by_id, created_at, updated_at, next_run, ...rest } = r as any;
        setForm(rest);
        const known = CRON_PRESETS.some((p) => p.value === r.cron);
        setCronPreset(known ? r.cron : "custom");
      });
    }
  }, [id]);

  useEffect(() => {
    datadogApi.fields(form.source_type).then(setFields);
  }, [form.source_type]);

  const runPreview = async () => {
    setPreviewing(true);
    try {
      const data = await datadogApi.preview(form.source_type, form.query, form.time_window);
      setPreview(data);
      if (form.columns.length === 0) set({ columns: data.fields });
    } catch (e: any) {
      notifications.show({ color: "red", message: "No se pudo obtener la vista previa" });
    } finally {
      setPreviewing(false);
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        timezone: SCHEDULER_TZ, // por ahora toda la programación corre en horario de Chile
        columns: form.columns.length ? form.columns : fields,
      };
      if (editing) await reportsApi.update(Number(id), payload);
      else await reportsApi.create(payload);
      notifications.show({ color: "green", message: "Reporte guardado" });
      nav("/");
    } catch (e: any) {
      notifications.show({
        color: "red",
        title: "Error al guardar",
        message: apiError(e, "Revisa los campos del reporte"),
      });
    } finally {
      setSaving(false);
    }
  };

  const next = () => setActive((a) => Math.min(a + 1, 4));
  const prev = () => setActive((a) => Math.max(a - 1, 0));

  return (
    <Stack maw={900} mx="auto">
      <Title order={2}>{editing ? "Editar reporte" : "Nuevo reporte"}</Title>

      <Card withBorder padding="xl" radius="md">
        <Stepper active={active} onStepClick={setActive} size="sm">
          {/* Paso 1: Datos básicos */}
          <Stepper.Step label="Datos" description="Equipo, nombre y descripción">
            <Stack mt="md">
              <Select
                label="Equipo propietario"
                description="Quién podrá ver y gestionar este reporte"
                required
                data={editableTeams}
                value={form.team_id ? String(form.team_id) : null}
                onChange={(v) => set({ team_id: v ? Number(v) : 0 })}
                disabled={editing}
                nothingFoundMessage="No tienes equipos con permiso de edición"
              />
              <TextInput
                label="Nombre del reporte"
                required
                value={form.name}
                onChange={(e) => set({ name: e.currentTarget.value })}
              />
              <Textarea
                label="Descripción"
                value={form.description}
                onChange={(e) => set({ description: e.currentTarget.value })}
              />
            </Stack>
          </Stepper.Step>

          {/* Paso 2: Fuente Datadog + preview + columnas */}
          <Stepper.Step label="Datos Datadog" description="Fuente y columnas">
            <Stack mt="md">
              <SimpleGrid cols={{ base: 1, sm: 3 }}>
                <Select
                  label="Fuente Datadog"
                  data={[
                    { value: "signals", label: "Security Signals" },
                    { value: "logs", label: "Logs" },
                    { value: "metrics", label: "Métricas (timeseries)" },
                  ]}
                  value={form.source_type}
                  onChange={(v) => set({ source_type: (v as any) || "signals", columns: [] })}
                />
                <Select
                  label="Ventana de tiempo"
                  data={WINDOWS}
                  value={form.time_window}
                  onChange={(v) => set({ time_window: v || "last_24h" })}
                />
                <TextInput
                  label={form.source_type === "metrics" ? "Query de métrica" : "Query Datadog"}
                  description={
                    form.source_type === "metrics"
                      ? "Ej: avg:system.cpu.user{*}"
                      : undefined
                  }
                  value={form.query}
                  onChange={(e) => set({ query: e.currentTarget.value })}
                  placeholder={
                    form.source_type === "metrics" ? "avg:system.cpu.user{*}" : "@severity:high"
                  }
                />
              </SimpleGrid>

              <Group>
                <Button variant="light" loading={previewing} onClick={runPreview}>
                  Vista previa
                </Button>
                {preview && (
                  <Text size="sm" c="dimmed">
                    {preview.total} fila(s) de muestra
                  </Text>
                )}
              </Group>

              <MultiSelect
                label="Columnas a incluir"
                data={fields}
                value={form.columns}
                onChange={(v) => set({ columns: v })}
                placeholder="Todas si se deja vacío"
                searchable
              />

              {preview && (
                <Paper withBorder p="xs" radius="sm">
                  <ScrollArea h={260}>
                    <Table striped withTableBorder fz="xs">
                      <Table.Thead>
                        <Table.Tr>
                          {(form.columns.length ? form.columns : preview.fields).map((c) => (
                            <Table.Th key={c}>{c}</Table.Th>
                          ))}
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {preview.rows.map((row, i) => (
                          <Table.Tr key={i}>
                            {(form.columns.length ? form.columns : preview.fields).map((c) => (
                              <Table.Td key={c}>{String((row as any)[c] ?? "")}</Table.Td>
                            ))}
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </ScrollArea>
                </Paper>
              )}
            </Stack>
          </Stepper.Step>

          {/* Paso 3: Formato + destinatarios */}
          <Stepper.Step label="Salida" description="Formato y correos">
            <Stack mt="md">
              <Select
                label="Formato de archivo"
                data={[
                  { value: "csv", label: "CSV" },
                  { value: "xlsx", label: "Excel (.xlsx)" },
                ]}
                value={form.output_format}
                onChange={(v) => set({ output_format: (v as any) || "csv" })}
                w={240}
              />
              <TagsInput
                label="Destinatarios (correos)"
                placeholder="Escribe un correo y Enter"
                value={form.recipients}
                onChange={(v) => set({ recipients: v })}
              />
              <Text size="xs" c="dimmed">
                El envío por correo está en modo simulado (mock) hasta cargar credenciales de Azure.
              </Text>
            </Stack>
          </Stepper.Step>

          {/* Paso 4: Programación */}
          <Stepper.Step label="Programación" description="Horario automático">
            <Stack mt="md">
              <SimpleGrid cols={{ base: 1, sm: 2 }}>
                <Select
                  label="Frecuencia"
                  data={CRON_PRESETS}
                  value={cronPreset}
                  onChange={(v) => {
                    setCronPreset(v || "custom");
                    if (v && v !== "custom") set({ cron: v });
                  }}
                />
                <TextInput
                  label="Zona horaria"
                  value="Chile continental (America/Santiago)"
                  readOnly
                  description="La programación se ejecuta en horario local de Chile"
                />
              </SimpleGrid>
              {cronPreset === "custom" && (
                <TextInput
                  label="Expresión cron (m h dom mon dow)"
                  value={form.cron}
                  onChange={(e) => set({ cron: e.currentTarget.value })}
                  placeholder="0 8 * * 1-5"
                />
              )}
              <Checkbox
                label="Reporte activo (se ejecuta automáticamente)"
                checked={form.enabled}
                onChange={(e) => set({ enabled: e.currentTarget.checked })}
              />
            </Stack>
          </Stepper.Step>

          <Stepper.Completed>
            <Stack mt="md" align="center">
              <Text>Todo listo para guardar el reporte.</Text>
            </Stack>
          </Stepper.Completed>
        </Stepper>

        <Group justify="space-between" mt="xl">
          <Button variant="default" onClick={() => nav("/")}>
            Cancelar
          </Button>
          <Group>
            {active > 0 && (
              <Button variant="default" onClick={prev}>
                Atrás
              </Button>
            )}
            {active < 4 ? (
              <Button
                onClick={next}
                disabled={active === 0 && (!form.name || !form.team_id)}
              >
                Siguiente
              </Button>
            ) : (
              <Button onClick={save} loading={saving} color="green">
                Guardar reporte
              </Button>
            )}
          </Group>
        </Group>
      </Card>
    </Stack>
  );
}
