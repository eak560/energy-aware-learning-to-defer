# Content for the upcoming slides

Material marked for the next review deck. Every source is in `papers/` and
`papers/references.bib`.

---

## Slide: Why the energy angle is real (robots as a leading example)

**Computing drains robot batteries, not just driving.**
A 2025 study measured real robots using 30–90 W in total, with the motors taking
only 16.6–54.6% of that. The rest goes mostly to computing and sensors.
*(Liu, Shi & Shin 2025, `liu2025powerefficientautonomousmobilerobots`)*

**Big models on board cost hours of battery.**
A 2026 measurement study found larger onboard GPUs "drain robot batteries several
hours faster". Sending work to a shared edge server helps, but adds delay and
network load, and robot fleets end up sharing that server.
*(Pohland et al. 2026, `pohland2026offloadoverloadplatformmeasurement`)*

**Robots care about sentiment.**
Reading how a person feels, including frustration, is an established goal in
human-robot interaction.
*(Spezialetti, Placidi & Rossi 2020, `spezialetti2020emotion`)*

> Speaker note: robots hear speech, so a speech-to-text step runs first; our
> router then works on the text. On robots, the on-device tier is the robot's
> own computer rather than an ESP32.

---

## Slide: Where energy-aware sentiment matters (use cases, ranked by fit)

Robots are one of the biggest use cases, not the only one.

| Use case | Runs on battery? | How text arrives | Runs on an ESP32? | Fit |
|---|---|---|---|---|
| Social, assistive or eldercare robots | Yes, a major constraint | Speech → text | No, the robot's onboard computer | Strongest story |
| Off-grid mesh messengers (e.g. LILYGO T-Deck running Meshtastic) | Yes | Typed on the device's keyboard | Yes, ESP32-S3: exact match | Best hardware match |
| Smartwatch with the phone as the hub | Yes, tiny battery | Voice replies and notes | Watch chip; phone is the hub | Believable |
| Kids' smart toys / companions | Yes | Speech | Often ESP32-class | Niche, privacy helps |
| Battery or solar feedback terminals | Yes | Typed feedback | Yes | Niche |
| Drones, smart speakers | Drones yes, speakers no | No text, or plugged in | — | Not a fit |

Sources: robots (above); off-grid messaging, `lilygo_tdeck` and HumAID
(`alam2021humaidhumanannotateddisasterincidents`, 77k disaster tweets including a
"requests or urgent needs" category).
