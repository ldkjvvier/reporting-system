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
} from '@mantine/core'
import {
	IconDownload,
	IconRefresh,
	IconArrowLeft,
	IconPlayerPlay,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiError, downloadUrl, getToken, reportsApi } from '../api'
import { useAuth } from '../auth'
import type { Report, ReportRun } from '../types'

const STATUS_COLOR: Record<string, string> = {
	pending: 'gray',
	running: 'blue',
	success: 'green',
	failed: 'red',
}

export default function RunHistory() {
	const { id } = useParams()
	const nav = useNavigate()
	const { canEdit } = useAuth()
	const reportId = Number(id)
	const [report, setReport] = useState<Report | null>(null)
	const [runs, setRuns] = useState<ReportRun[]>([])

	// Solo admins/editores del equipo pueden disparar ejecuciones (el backend lo exige).
	const canRun = report ? canEdit(report.team_id) : false

	const load = async () => {
		const [r, rs] = await Promise.all([
			reportsApi.get(reportId),
			reportsApi.runs(reportId),
		])
		setReport(r)
		setRuns(rs)
	}

	useEffect(() => {
		load()
		const t = setInterval(load, 4000) // refresco para ver corridas en curso
		return () => clearInterval(t)
	}, [id])

	const download = async (run: ReportRun) => {
		// Descarga autenticada: pide el archivo con el token y fuerza el guardado.
		const res = await fetch(downloadUrl(run.id), {
			headers: { Authorization: `Bearer ${getToken()}` },
		})
		if (!res.ok) {
			notifications.show({
				color: 'red',
				message: 'Archivo no disponible',
			})
			return
		}
		const blob = await res.blob()
		const url = URL.createObjectURL(blob)
		const a = document.createElement('a')
		a.href = url
		a.download =
			run.file_path?.split(/[\\/]/).pop() || `reporte_${run.id}`
		a.click()
		URL.revokeObjectURL(url)
	}

	const runNow = async () => {
		try {
			await reportsApi.runNow(reportId)
			notifications.show({
				color: 'blue',
				message: 'Ejecución encolada',
			})
			setTimeout(load, 1500)
		} catch (e: any) {
			notifications.show({
				color: 'red',
				message: apiError(e, 'No se pudo ejecutar'),
			})
		}
	}

	return (
		<Stack maw={1000} mx="auto">
			<Group justify="space-between">
				<Group>
					<ActionIcon variant="subtle" onClick={() => nav('/')}>
						<IconArrowLeft />
					</ActionIcon>
					<div>
						<Title order={2}>Historial de ejecuciones</Title>
						<Text c="dimmed">{report?.name}</Text>
					</div>
				</Group>
				<Group>
					<Button
						variant="light"
						leftSection={<IconRefresh size={16} />}
						onClick={load}
					>
						Actualizar
					</Button>
					{canRun && (
						<Button
							leftSection={<IconPlayerPlay size={16} />}
							color="green"
							onClick={runNow}
						>
							Ejecutar ahora
						</Button>
					)}
				</Group>
			</Group>

			<Card withBorder radius="md" padding="lg">
				{runs.length === 0 ? (
					<Text c="dimmed" ta="center" py="xl">
						Sin corridas todavía. Usa “Ejecutar ahora” o espera a la
						programación.
					</Text>
				) : (
					<Table.ScrollContainer minWidth={720}>
						<Table verticalSpacing="sm" highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>#</Table.Th>
									<Table.Th>Estado</Table.Th>
									<Table.Th>Disparo</Table.Th>
									<Table.Th>Inicio</Table.Th>
									<Table.Th>Filas</Table.Th>
									<Table.Th>Envío</Table.Th>
									<Table.Th ta="right">Archivo</Table.Th>
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{runs.map((run) => (
									<Table.Tr key={run.id}>
										<Table.Td>{run.id}</Table.Td>
										<Table.Td>
											<Badge
												color={STATUS_COLOR[run.status]}
												variant="light"
											>
												{run.status}
											</Badge>
											{run.error_message && (
												<Text size="xs" c="red" maw={260} truncate>
													{run.error_message}
												</Text>
											)}
										</Table.Td>
										<Table.Td>
											{run.trigger === 'scheduled'
												? 'Programado'
												: 'Manual'}
										</Table.Td>
										<Table.Td>
											{new Date(run.started_at).toLocaleString()}
										</Table.Td>
										<Table.Td>{run.row_count}</Table.Td>
										<Table.Td>
											{run.delivery_status ? (
												<Badge
													variant="dot"
													color={
														run.delivery_status === 'failed'
															? 'red'
															: 'teal'
													}
												>
													{run.delivery_status}
												</Badge>
											) : (
												'—'
											)}
										</Table.Td>
										<Table.Td ta="right">
											{run.file_path ? (
												<Tooltip label="Descargar">
													<ActionIcon
														variant="subtle"
														onClick={() => download(run)}
													>
														<IconDownload size={18} />
													</ActionIcon>
												</Tooltip>
											) : (
												'—'
											)}
										</Table.Td>
									</Table.Tr>
								))}
							</Table.Tbody>
						</Table>
					</Table.ScrollContainer>
				)}
			</Card>
		</Stack>
	)
}
