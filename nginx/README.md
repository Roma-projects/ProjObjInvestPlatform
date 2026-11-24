# Nginx / Frontend Edge

Nginx отдаёт клиент, проксирует `/api/` в API Gateway, WebSocket уведомлений — в Notification, а публичные загрузки читает из read-only volume. Контейнер использует непривилегированный пользователь и слушает порт `8080`.

## Docker Compose

```powershell
docker compose up --build -d nginx
docker compose logs -f nginx
```

Сервис доступен на `http://localhost:8080` для локальной разработки. В Kubernetes TLS должен завершаться на Ingress или другом TLS-терминаторе. Он должен перенаправлять HTTP на HTTPS и перезаписывать `X-Forwarded-Proto` и `X-Forwarded-For`; не публикуйте Nginx в обход этого прокси.

Для корректного IP-лимита Gateway добавьте реальные CIDR ingress/load balancer в `nginx/trusted-proxies.conf`, например `set_real_ip_from 10.42.0.0/16;`. Не указывайте подсети, в которых находятся недоверенные workloads. Конфигурация также сохраняет доверенную схему `https`, чтобы внутренние сервисы получали правильный `X-Forwarded-Proto`.

Ограничение API-тела по умолчанию — 2 MiB, загрузки объявлений — 105 MiB вместе с multipart-обвязкой, аватар — 6 MiB. Gateway дополнительно потоково ограничивает входящий запрос; Listing проверяет сигнатуры файлов и декодирует/повторно кодирует публичные изображения.

Завершение внешнего TLS само по себе не шифрует связь Ingress→Nginx и между Pod. Требования для Kubernetes, mTLS и шифрования хранилищ описаны в [`SECURITY_DEPLOYMENT.md`](../SECURITY_DEPLOYMENT.md).

## Ручная сборка

```powershell
docker build -f nginx/Dockerfile -t business-platform-nginx .
```

В обычной разработке запускайте Nginx через Compose: ему нужны внутренняя сеть и read-only mounts `public_uploads` и `auth_avatars`.
