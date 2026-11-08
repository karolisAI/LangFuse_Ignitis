"""Download a reproducible upstream Compose configuration and generate local secrets."""
import secrets
from pathlib import Path
from urllib.request import urlopen

REVISION = "02fb648b58df0b22578b5d5f10b2bb61c39e0486"
ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / "infra" / ".runtime"
    target.mkdir(parents=True, exist_ok=True)
    compose = target / "compose.yaml"
    env = target / ".env"
    if compose.exists() or env.exists():
        raise SystemExit("Existing setup retained. Use infra/.runtime; no files overwritten.")
    url = f"https://raw.githubusercontent.com/langfuse/langfuse/{REVISION}/docker-compose.yml"
    with urlopen(url, timeout=30) as response:
        content = response.read().decode()
    # Upstream exposes web and object-storage UI; keep this PoC local to the host.
    for port in ('3000:3000', '9090:9000', '9091:9001',
                 '${LANGFUSE_AI_GATEWAY_PORT:-3031}:${LANGFUSE_AI_GATEWAY_PORT:-3031}'):
        content = content.replace(f'- {port}', f'- 127.0.0.1:{port}')
    values = {"LANGFUSE_IMAGE_TAG": "4.76.0", "TELEMETRY_ENABLED": "false"}
    for key in ("SALT", "ENCRYPTION_KEY", "NEXTAUTH_SECRET", "POSTGRES_PASSWORD",
                "CLICKHOUSE_PASSWORD", "REDIS_AUTH", "MINIO_ROOT_PASSWORD"):
        values[key] = secrets.token_hex(32)
    values["DATABASE_URL"] = (
        f"postgresql://postgres:{values['POSTGRES_PASSWORD']}@postgres:5432/postgres"
    )
    for prefix in ("EVENT_UPLOAD", "MEDIA_UPLOAD", "BATCH_EXPORT"):
        values[f"LANGFUSE_S3_{prefix}_SECRET_ACCESS_KEY"] = values["MINIO_ROOT_PASSWORD"]
    env.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
    compose.write_text(content, encoding="utf-8")
    print("Created infra/.runtime/compose.yaml and generated secrets in .env (gitignored).")


if __name__ == "__main__":
    main()
