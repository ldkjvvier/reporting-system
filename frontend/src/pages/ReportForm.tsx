import {
  Badge,
  Button,
  Card,
  Checkbox,
  Grid,
  Group,
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
import { IconAlertCircle } from "@tabler/icons-react";
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

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Campos obligatorios de cada paso del Stepper. Se usa para bloquear el avance
// y para marcar el paso en rojo cuando falta completar algo.
const STEP_FIELDS: Record<number, string[]> = {
  0: ["team_id", "name"],
  1: ["query"],
  2: ["recipients"],
  3: ["cron"],
};

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
  // Pasos cuyos errores ya deben mostrarse (el usuario intentó avanzar desde ahí).
  const [touched, setTouched] = useState<Set<number>>(new Set());

  const set = (patch: Partial<ReportInput>) => setForm((f) => ({ ...f, ...patch }));

  // Errores de validación por campo. Los destinatarios son opcionales: solo se
  // valida el formato de los correos que se hayan escrito.
  const fieldErrors = useMemo(() => {
    const e: Record<string, string> = {};
    if (!form.team_id) e.team_id = "Selecciona un equipo propietario";
    if (!form.name.trim()) e.name = "Ingresa un nombre para el reporte";
    if (!form.query.trim()) e.query = "Ingresa una query de Datadog";
    const badEmail = form.recipients.find((r) => !EMAIL_RE.test(r));
    if (badEmail) e.recipients = `Correo inválido: ${badEmail}`;
    if (!form.cron.trim()) e.cron = "Define la frecuencia de ejecución";
    else if (cronPreset === "custom" && form.cron.trim().split(/\s+/).length !== 5)
      e.cron = "La expresión cron debe tener 5 campos (m h dom mon dow)";
    return e;
  }, [form, cronPreset]);

  const stepHasError = (step: number) =>
    STEP_FIELDS[step]?.some((f) => fieldErrors[f]) ?? false;

  // Muestra el error de un campo solo si su paso ya fue "tocado".
  const showErr = (field: string, step: number) =>
    touched.has(step) ? fieldErrors[field] : undefined;

  const markTouched = (step: number) =>
    setTouched((t) => new Set(t).add(step));

  // Equipos donde el usuario puede crear/editar: todos si es admin, o aquellos
  // en los que tiene rol 'editor'.
  const editableTeams = useMemo(() => {
    if (isAdmin) return allTeams.map((t) => ({ value: String(t.id), label: t.name }));
    return (user?.memberships ?? [])
      .filter((m) => m.role === "editor")
      .map((m) => ({ value: String(m.team_id), label: m.team_name }));
  }, [isAdmin, allTeams, user]);

  // Campos ofrecidos como sugerencia: tras la vista previa, todos los descubiertos
  // en la muestra (incluye anidados en notación de punto, p. ej. attributes.http.method);
  // antes de previsualizar, la lista curada por fuente.
  const selectable = useMemo(
    () => (preview?.available_fields?.length ? preview.available_fields : fields),
    [preview, fields],
  );

  // Cobertura de cada campo en la muestra de la vista previa: fracción de filas
  // con valor no vacío. Permite mostrar al usuario qué columnas traen datos y
  // cuáles vendrán vacías, sin necesidad de ser técnico. Solo disponible tras
  // pulsar "Vista previa".
  const coverage = useMemo<Record<string, number>>(() => {
    if (!preview || preview.rows.length === 0) return {};
    const total = preview.rows.length;
    const cov: Record<string, number> = {};
    for (const f of selectable) {
      let filled = 0;
      for (const row of preview.rows) {
        const v = (row as any)[f];
        if (v !== null && v !== undefined && String(v).trim() !== "") filled++;
      }
      cov[f] = filled / total;
    }
    return cov;
  }, [preview, selectable]);

  const hasCoverage = Object.keys(coverage).length > 0;
  // Columnas incluidas que vinieron totalmente vacías en la muestra (aviso suave).
  const emptyIncluded = useMemo(
    () => form.columns.filter((c) => coverage[c] === 0),
    [form.columns, coverage],
  );

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
    // Revalida todo el formulario antes de enviar; salta al primer paso con error.
    const firstBad = [0, 1, 2, 3].find((s) => stepHasError(s));
    if (firstBad !== undefined) {
      setTouched(new Set([0, 1, 2, 3]));
      setActive(firstBad);
      notifications.show({
        color: "red",
        message: "Hay campos requeridos sin completar",
      });
      return;
    }
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

  const next = () => {
    if (stepHasError(active)) {
      markTouched(active);
      notifications.show({
        color: "red",
        message: "Completa los campos requeridos antes de continuar",
      });
      return;
    }
    setActive((a) => Math.min(a + 1, 4));
  };
  const prev = () => setActive((a) => Math.max(a - 1, 0));

  // Permite retroceder libremente, pero bloquea saltar a un paso posterior si
  // algún paso intermedio tiene campos sin completar.
  const handleStepClick = (target: number) => {
    if (target <= active) {
      setActive(target);
      return;
    }
    for (let s = active; s < target; s++) {
      if (stepHasError(s)) {
        markTouched(s);
        setActive(s);
        notifications.show({
          color: "red",
          message: "Completa los campos requeridos antes de continuar",
        });
        return;
      }
    }
    setActive(target);
  };

  // Texto legible de la frecuencia elegida, para el resumen final.
  const cronLabel =
    CRON_PRESETS.find((p) => p.value === form.cron && p.value !== "custom")?.label ??
    form.cron;
  const teamLabel =
    editableTeams.find((t) => t.value === String(form.team_id))?.label ?? "—";

  // Contenido del paso activo. Se renderiza en el panel ancho de la derecha; el
  // rail vertical de la izquierda solo gobierna la navegación entre pasos.
  const renderStep = () => {
    switch (active) {
      // Paso 1: Datos básicos
      case 0:
        return (
          <Stack>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <Select
                label="Equipo propietario"
                description="Quién podrá ver y gestionar este reporte"
                required
                data={editableTeams}
                value={form.team_id ? String(form.team_id) : null}
                onChange={(v) => set({ team_id: v ? Number(v) : 0 })}
                disabled={editing}
                nothingFoundMessage="No tienes equipos con permiso de edición"
                error={showErr("team_id", 0)}
              />
              <TextInput
                label="Nombre del reporte"
                required
                value={form.name}
                onChange={(e) => set({ name: e.currentTarget.value })}
                error={showErr("name", 0)}
              />
            </SimpleGrid>
            <Textarea
              label="Descripción"
              autosize
              minRows={3}
              value={form.description}
              onChange={(e) => set({ description: e.currentTarget.value })}
            />
          </Stack>
        );

      // Paso 2: Fuente Datadog + preview + columnas
      case 1:
        return (
          <Stack>
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
                  form.source_type === "metrics" ? "Ej: avg:system.cpu.user{*}" : undefined
                }
                value={form.query}
                onChange={(e) => set({ query: e.currentTarget.value })}
                required
                error={showErr("query", 1)}
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

            <Stack gap={6}>
              <TagsInput
                label="Columnas a incluir"
                description={
                  hasCoverage
                    ? "Elige de la lista o escribe un campo anidado (p. ej. attributes.http.method) y Enter. El color indica cuántos datos trae en la muestra."
                    : "Pulsa «Vista previa» para descubrir los campos disponibles, o escribe uno (p. ej. attributes.http.method) y Enter."
                }
                data={selectable}
                value={form.columns}
                onChange={(v) => set({ columns: v })}
                placeholder={form.columns.length ? "" : "Todas si se deja vacío"}
                clearable
                renderOption={({ option }) => (
                  <Group gap="xs" wrap="nowrap" w="100%">
                    <Text size="sm" style={{ flex: 1 }}>
                      {option.value}
                    </Text>
                    <CoverageBadge value={coverage[option.value]} />
                  </Group>
                )}
              />

              {hasCoverage && (
                <Group gap="xs">
                  <Button
                    size="compact-xs"
                    variant="light"
                    onClick={() =>
                      set({ columns: selectable.filter((f) => (coverage[f] ?? 0) > 0) })
                    }
                  >
                    Solo columnas con datos
                  </Button>
                  <Button
                    size="compact-xs"
                    variant="subtle"
                    onClick={() => set({ columns: [...selectable] })}
                  >
                    Incluir todas
                  </Button>
                </Group>
              )}

              {emptyIncluded.length > 0 && (
                <Text size="xs" c="orange.7">
                  Incluirás {emptyIncluded.length} columna(s) vacía(s) en la muestra:{" "}
                  {emptyIncluded.join(", ")}. Aparecerán sin datos si tampoco vienen al
                  ejecutar el reporte.
                </Text>
              )}
            </Stack>

            {preview && (
              <Paper withBorder p="xs" radius="sm">
                <ScrollArea h={420}>
                  <Table striped withTableBorder fz="xs" stickyHeader>
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
        );

      // Paso 3: Formato + destinatarios
      case 2:
        return (
          <Stack>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <Select
                label="Formato de archivo"
                data={[
                  { value: "csv", label: "CSV" },
                  { value: "xlsx", label: "Excel (.xlsx)" },
                ]}
                value={form.output_format}
                onChange={(v) => set({ output_format: (v as any) || "csv" })}
              />
              <TagsInput
                label="Destinatarios (correos)"
                placeholder="Escribe un correo y Enter"
                value={form.recipients}
                onChange={(v) => set({ recipients: v })}
                error={showErr("recipients", 2)}
              />
            </SimpleGrid>
            <Text size="xs" c="dimmed">
              El envío por correo está en modo simulado (mock) hasta cargar credenciales de Azure.
            </Text>
          </Stack>
        );

      // Paso 4: Programación
      case 3:
        return (
          <Stack>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <Select
                label="Frecuencia"
                data={CRON_PRESETS}
                value={cronPreset}
                onChange={(v) => {
                  setCronPreset(v || "custom");
                  if (v && v !== "custom") set({ cron: v });
                }}
                error={cronPreset !== "custom" ? showErr("cron", 3) : undefined}
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
                error={showErr("cron", 3)}
                placeholder="0 8 * * 1-5"
              />
            )}
            <Checkbox
              label="Reporte activo (se ejecuta automáticamente)"
              checked={form.enabled}
              onChange={(e) => set({ enabled: e.currentTarget.checked })}
            />
          </Stack>
        );

      // Paso final: resumen antes de guardar
      default:
        return (
          <Stack>
            <Text c="dimmed">Revisa la configuración antes de guardar el reporte.</Text>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
              <SummaryItem label="Nombre" value={form.name || "—"} />
              <SummaryItem label="Equipo" value={teamLabel} />
              <SummaryItem
                label="Fuente"
                value={
                  { signals: "Security Signals", logs: "Logs", metrics: "Métricas" }[
                    form.source_type
                  ]
                }
              />
              <SummaryItem
                label="Ventana"
                value={WINDOWS.find((w) => w.value === form.time_window)?.label ?? form.time_window}
              />
              <SummaryItem
                label="Columnas"
                value={form.columns.length ? `${form.columns.length} seleccionadas` : "Todas"}
              />
              <SummaryItem label="Formato" value={form.output_format.toUpperCase()} />
              <SummaryItem
                label="Destinatarios"
                value={form.recipients.length ? `${form.recipients.length} correo(s)` : "Ninguno"}
              />
              <SummaryItem label="Frecuencia" value={cronLabel} />
              <SummaryItem label="Estado" value={form.enabled ? "Activo" : "Pausado"} />
            </SimpleGrid>
          </Stack>
        );
    }
  };

  return (
    <Stack maw={1280} mx="auto">
      <div>
        <Title order={2}>{editing ? "Editar reporte" : "Nuevo reporte"}</Title>
        <Text c="dimmed">Configura la fuente, el formato y la programación del reporte</Text>
      </div>

      <Grid gutter="lg" align="stretch">
        {/* Rail de pasos (navegación + progreso) */}
        <Grid.Col span={{ base: 12, md: 4, lg: 3 }}>
          <Card withBorder padding="lg" radius="md" h="100%">
            <Stepper
              active={active}
              onStepClick={handleStepClick}
              allowNextStepsSelect={false}
              orientation="vertical"
              size="sm"
            >
              <Stepper.Step
                label="Datos"
                description="Equipo, nombre y descripción"
                color={touched.has(0) && stepHasError(0) ? "red" : undefined}
                completedIcon={
                  touched.has(0) && stepHasError(0) ? <IconAlertCircle size={18} /> : undefined
                }
              />
              <Stepper.Step
                label="Datos Datadog"
                description="Fuente y columnas"
                color={touched.has(1) && stepHasError(1) ? "red" : undefined}
                completedIcon={
                  touched.has(1) && stepHasError(1) ? <IconAlertCircle size={18} /> : undefined
                }
              />
              <Stepper.Step
                label="Salida"
                description="Formato y correos"
                color={touched.has(2) && stepHasError(2) ? "red" : undefined}
                completedIcon={
                  touched.has(2) && stepHasError(2) ? <IconAlertCircle size={18} /> : undefined
                }
              />
              <Stepper.Step
                label="Programación"
                description="Horario automático"
                color={touched.has(3) && stepHasError(3) ? "red" : undefined}
                completedIcon={
                  touched.has(3) && stepHasError(3) ? <IconAlertCircle size={18} /> : undefined
                }
              />
            </Stepper>
          </Card>
        </Grid.Col>

        {/* Panel de contenido del paso activo */}
        <Grid.Col span={{ base: 12, md: 8, lg: 9 }}>
          <Card withBorder padding="xl" radius="md" h="100%">
            <Stack h="100%" justify="space-between" gap="lg">
              <div>{renderStep()}</div>

              <Group
                justify="space-between"
                pt="md"
                style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}
              >
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
                    <Button onClick={next}>Siguiente</Button>
                  ) : (
                    <Button onClick={save} loading={saving} color="green">
                      Guardar reporte
                    </Button>
                  )}
                </Group>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

// Par etiqueta/valor para el resumen final del reporte.
function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: "0.05em" }}>
        {label}
      </Text>
      <Text size="sm" fw={500}>
        {value}
      </Text>
    </Stack>
  );
}

// Etiqueta de cobertura de un campo en la muestra de la vista previa.
// value es la fracción de filas con dato (0..1) o undefined si aún no hay preview.
function CoverageBadge({ value }: { value: number | undefined }) {
  if (value === undefined) return null;
  const pct = Math.round(value * 100);
  if (value >= 0.999)
    return <Badge size="xs" variant="light" color="green">con datos</Badge>;
  if (value > 0)
    return (
      <Badge size="xs" variant="light" color="yellow">
        a veces vacío ({pct}%)
      </Badge>
    );
  return <Badge size="xs" variant="light" color="gray">vacío en la muestra</Badge>;
}
