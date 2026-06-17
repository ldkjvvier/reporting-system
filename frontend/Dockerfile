# syntax=docker/dockerfile:1
# --- Build ---
# Node 22 LTS (la 20 entró en EOL en 2026; sin parches de seguridad).
FROM node:22-alpine AS build
WORKDIR /app
# Copiamos package.json y el lockfile para usar `npm ci`: instalacion
# determinista y mucho mas rapida que `npm install` (sin resolver el arbol),
# respetando exactamente las versiones auditadas del lockfile.
COPY package.json package-lock.json ./
# Cache de npm entre builds para acelerar reconstrucciones (requiere BuildKit).
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build

# --- Runtime (Nginx) ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
