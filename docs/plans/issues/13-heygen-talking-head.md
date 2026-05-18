## Parent PRD

#{{PARENT}}

## What to build

Generazione video talking-head con avatar brand partendo da uno script generato dal Content Engine.

Riferimento PRD §3.4.

## Acceptance criteria

- [ ] `services/video/heygen_client.py` (auth, list avatars, generate video, poll status)
- [ ] Chiave Heygen per-brand in `brand_integrations`
- [ ] UI Settings → Brand → Video → "Heygen avatar": select avatar default per-brand
- [ ] Endpoint `POST /api/video/generate` con kind="talking-head", input=script
- [ ] Bottone "Generate talking-head" in writing-lab per draft di tipo "video script"
- [ ] Quota per-brand in `feature_flags` (es. `heygen_minutes_per_month`), enforce con counter mensile
- [ ] Alert Telegram quando un brand supera 80% della quota
- [ ] Video Heygen completato → mirror in tabella `videos` (type='heygen')
- [ ] Test integrazione contro sandbox Heygen

## Blocked by

- Blocked by #{{1}}
- Blocked by #{{11}}

## User stories addressed

- US-V3 (talking-head da script)
