import React from "react";
import ReactDOM from "react-dom/client";
import { MantineProvider, createTheme } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { BrowserRouter } from "react-router-dom";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "./ui.css";

import App from "./App";
import { AuthProvider } from "./auth";

const theme = createTheme({
  primaryColor: "blue",
  colors: {
    blue: [
      "#EFF6FF",
      "#DBEAFE",
      "#BFDBFE",
      "#93C5FD",
      "#60A5FA",
      "#3B82F6",
      "#2563EB",
      "#1D4ED8",
      "#1E40AF",
      "#1E3A8A",
    ],
  },
  fontFamily:
    'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  headings: { fontWeight: "600" },
  defaultRadius: "sm",
  components: {
    Table: {
      styles: {
        thead: {
          backgroundColor: "#F8FAFC",
          borderBottom: "2px solid #E2E8F0",
        },
        th: {
          fontWeight: "600",
          fontSize: "11px",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "#64748B",
        },
      },
    },
    Card: {
      defaultProps: { shadow: "xs" },
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Notifications position="top-right" />
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </MantineProvider>
  </React.StrictMode>
);
