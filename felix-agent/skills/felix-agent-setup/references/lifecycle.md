# Local lifecycle

Work in the selected starter directory. Use `docker compose ps`, the mapped loopback port, and `/healthz` for status. Treat logs and configuration as sensitive; inspect only necessary diagnostics and redact credentials, prompts, personal data and tokens before sharing. Stopping or restarting a running service interrupts work; explain this when relevant.

## Backup

Before upgrade or migration, stop Felix and any setup container and confirm they stopped. Run `python3 <plugin-root>/scripts/backup.py <installation>` (Windows: `py -3` where appropriate). Python 3 is required. The script archives only `.env` in the user's `~/.felix-agent-backups` outside the live installation, verifies archive integrity and the file hash, then atomically replaces the previous backup for that installation. The backup contains secrets. On Unix it restricts the directory to the user; on Windows confirm the directory's inherited ACL protects it, and if not, secure it before placing sensitive data there. If backup fails, preserve the previous backup, restore the original running state if appropriate, and do not upgrade or migrate. Report that workspace data is not backed up; upstream recommends backing up the complete workspace before upgrading. Do not print backup contents.

## Upgrade

Record the current image reference and running state without revealing configuration. Make the verified backup above. Follow the installed starter and current official upgrade instructions, selecting the requested released image/tag or digest; pull, start, and verify health. Preserve the previous image reference and `.env` backup for rollback; the backup cannot restore workspace data. If upgrade fails, report the failure and offer rollback; do not delete the backup. Restart previously running services when safe.

## Migration

Identify source, standard destination, interruption, and backup path and show a concrete plan; obtain user approval before moving. Refuse to overwrite a destination. Back up the stopped source first, preserve the original until the destination passes verification, and move/copy all required starter files including ignored `.env` and the entire workspace with permissions preserved. Check custom mounts, absolute paths and Compose project identity before deciding whether they need user-directed adjustment. Start at the destination only when safe and verify configuration and health. If verification fails, stop the destination and leave the original and backup intact for recovery. Do not remove the original without explicit user authorization. Explain that Docker Compose project names and generated container names may change. Migration of unusual mounts or platforms without reliable permission preservation requires manual handling.
