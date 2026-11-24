# Security deployment notes

The repository has no Kubernetes workload, Ingress, NetworkPolicy, StorageClass, or Secret manifests. Compose hardening is configured in the repository; cluster controls below must be applied to the actual cluster before exposing it.

## Kubernetes TLS and network boundaries

- Configure a TLS certificate on the public Ingress, redirect HTTP to HTTPS, and set HSTS at the TLS edge. Point the Ingress Service to Nginx port `8080`.
- Restrict Nginx to traffic from the Ingress/load balancer. The Ingress must overwrite `X-Forwarded-Proto` and `X-Forwarded-For`; add only its real source CIDRs to `nginx/trusted-proxies.conf`. Otherwise client IP rate limits will see the proxy address, or forwarded headers could be spoofed.
- Ingress TLS termination encrypts browser→Ingress only. It does not encrypt Ingress→Nginx or pod-to-pod connections. Use a service mesh with strict mTLS for all service traffic, or configure TLS on each backend and point service URLs/DSNs at verified TLS endpoints. Keep certificate verification enabled and provide the right CA bundle.
- Apply default-deny NetworkPolicies in the application namespace and allow only the required flows: Ingress→Nginx; Nginx→Gateway/Notification; Gateway→API services; each service→its own database/cache plus the required broker and external providers. Database, Redis, and RabbitMQ services should have no public Service or host port.
- Store JWT, service-to-service and datastore passwords in Kubernetes Secrets backed by encryption at rest/KMS and narrow RBAC, or an external secret manager. Enable encryption at rest for etcd and persistent volumes at the cluster/provider layer. Docker named volumes in local Compose are not encrypted.

The application URL settings accept HTTPS/TLS schemes (`https://`, `rediss://`, `amqps://`, Mongo `tls=true`, and PostgreSQL `ssl=require`) so they can target TLS-enabled cluster services. Compose defaults use private bridge networking for development and do not provide end-to-end service mTLS or encrypted volumes.

## Pod security context

All Python Docker images now run as UID/GID `10001`, with a read-only root filesystem, no privilege escalation, dropped Linux capabilities, and writable `/tmp` only in Compose. Nginx uses the unprivileged image. Apply the equivalent settings to every Kubernetes container and init container:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop: ["ALL"]
```

Set `fsGroup: 10001` or use a narrowly scoped volume-permissions init container for Listing uploads, Auth avatars, and Parser storage. Nginx uses UID `101`. Do not run the application containers privileged.

## Application protections in this repository

- Auth signs access/refresh JWTs with an RSA private key; only Auth receives it. Gateway has the corresponding public key and verifies RS256, so compromise of Gateway or another API service does not permit token signing. Gateway checks account blocks and moderator roles, strips caller-supplied identity headers, and uses a different 256-bit service token for each downstream. Auth↔Moderation and Listing↔Moderation use separate service tokens.
- The switch from HS256 invalidates existing access, refresh, and email-verification JWTs. Deploy the matching key pair to Auth and Gateway together; users must sign in again after deployment.
- Auth email verification uses an 8-digit one-time code bound to a short-lived challenge cookie, invalidates prior codes, allows five invalid guesses per challenge, and limits verification requests by IP. Email delivery has its own per-address limits.
- PostgreSQL roles/databases, MongoDB users/databases, and Redis ACL users are separated by service. Bootstrap jobs migrate existing PostgreSQL ownership and create MongoDB application users without removing data.
- User values in SQLAlchemy operations are bound parameters. The few fixed SQL statements in migration bootstrap are constants; the moderation database name is restricted to alphanumerics/underscore before quoting.
- Public raster uploads are decoded and re-encoded, limited to 25 million pixels, and stripped of metadata. PDF/MP4/MOV signatures are checked; uploads are streamed with size limits and IP rate limits.
- Python dependencies still use broad lower-bound requirements rather than a committed lockfile. CI must resolve and run an automated vulnerability audit on every dependency update and on a schedule; a successful audit is required before release.

## Existing MongoDB volume migration

The previous Compose configuration used MongoDB without authentication. Before recreating `mongo` with `--auth`, use the existing running MongoDB container (still on the old, unauthenticated Compose configuration) and the new root `.env` values:

```powershell
docker compose run --rm --no-deps mongo-legacy-auth-migration
docker compose up -d --force-recreate mongo
docker compose up --build -d
```

The migration job creates the MongoDB admin user and per-database application users in the existing data volume. It is idempotent. If the unauthenticated MongoDB container is already stopped, start the old configuration first; do not start an old data volume with `--auth` before the first admin user has been created.

`postgres-bootstrap` runs on startup and creates/upgrades the app roles, databases, and ownership in place. It does not drop databases or volumes.

## Dependency audit

Requirements are not pinned, so this repository cannot claim a fixed CVE inventory. Resolve compatible versions into a reviewed lockfile and run `pip-audit` against that lockfile in CI before production release. Update the lockfile and scan report as part of dependency upgrades.
