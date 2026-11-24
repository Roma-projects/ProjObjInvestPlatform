# Упаковывает конфигурацию Nginx и статический клиентский интерфейс.
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/trusted-proxies.conf /etc/nginx/trusted-proxies.conf
COPY frontend/ /usr/share/nginx/html/
