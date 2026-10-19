# Nginx / Frontend Edge

Nginx отдаёт собранную веб-страницу, проксирует `/api/` в API Gateway, прокидывает WebSocket уведомлений и читает публичные загрузки только из read-only volume.

## Запуск через Docker Compose

```powershell
docker compose up --build -d nginx
docker compose logs -f nginx
```

Веб-приложение доступно на `http://localhost:8080`. Загрузка тела запроса ограничена настройкой Nginx в соответствии с лимитом Listing.

## Сборка вручную

```powershell
docker build -f nginx/Dockerfile -t business-platform-nginx .
```

В обычной разработке запускайте Nginx через Compose: ему нужна внутренняя сеть Compose и read-only mount `public_uploads`.
