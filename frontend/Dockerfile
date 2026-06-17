# --- Build ---
# Node 22 LTS sobre Debian (slim), no Alpine: el build de dependencias grandes
# (p. ej. @tabler/icons-react) provocaba en Alpine el fallo de npm
# "Exit handler never called" (por musl/OOM). Debian lo evita.
FROM node:22-slim AS build
WORKDIR /app
# Copiamos package.json y el lockfile primero (capa cacheable): mientras no
# cambien, Docker reutiliza la capa de 'npm ci' y el build es casi instantaneo.
# Usamos 'npm ci' (determinista y mas rapido que 'npm install', respeta el
# lockfile auditado). Compatible con el builder clasico y con BuildKit.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --fund=false
COPY . .
RUN npm run build

# --- Runtime (Nginx) ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
