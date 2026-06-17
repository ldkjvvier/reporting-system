import {
  Button,
  Center,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconReportAnalytics } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    try {
      await login(email, password);
      nav("/");
    } catch (e: any) {
      notifications.show({
        color: "red",
        title: "Error",
        message: e?.response?.data?.detail || "No se pudo autenticar",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Center mih="100vh" bg="gray.1">
      <div
        style={{
          width: 420,
          borderRadius: 8,
          overflow: "hidden",
          boxShadow: "0 4px 24px rgba(0,0,0,0.14)",
        }}
      >
        {/* Cabecera de marca */}
        <Stack
          align="center"
          gap={6}
          py={32}
          px={32}
          style={{ backgroundColor: "#0D1F35" }}
        >
          <IconReportAnalytics size={40} color="#60A5FA" />
          <Title order={3} c="white" mt={4} ta="center">
            Reportería Automatizada
          </Title>
          <Text c="blue.3" size="sm">
            Datadog Cloud SIEM
          </Text>
        </Stack>

        {/* Formulario */}
        <Stack p={32} bg="white">
          <TextInput
            label="Correo corporativo"
            placeholder="nombre@empresa.com"
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
          />
          <PasswordInput
            label="Contraseña"
            value={password}
            onChange={(e) => setPassword(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
          <Button onClick={submit} loading={loading} fullWidth mt={4}>
            Iniciar sesión
          </Button>
          <Text size="xs" c="dimmed" ta="center">
            Sin acceso? Solicítalo a un administrador.
          </Text>
        </Stack>
      </div>
    </Center>
  );
}
