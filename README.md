<p align="center">
  <img src="assets/images/logo.png" alt="Tailscale Controller logo" width="104">
</p>

<h1 align="center">Tailscale Controller</h1>

<p align="center">
  A tiny GTK desktop control panel for Tailscale on Linux.
</p>

<p align="center">
  <strong>Unofficial.</strong>
  <strong>Not affiliated with Tailscale.</strong>
  <strong>Just a homemade GUI experiment.</strong>
</p>

---

> [!WARNING]
> This repository is **not an official Tailscale project**.
> It is **not** made by Tailscale, **not** endorsed by Tailscale, and **not** affiliated with Tailscale Inc.
> If you want the supported, polished, official experience, please use the real Tailscale client.

## About

Tailscale Controller is a small personal Linux GUI built around the `tailscale` CLI.
The goal is simple: give Tailscale a cute little desktop panel for quick checks, quick toggles, and quick peeking at your devices.

It is intentionally lightweight, a bit handmade, and very much **not** pretending to be an official client.

## Highlights

- Simple home screen with a big connection toggle
- Status page for your device and peer devices
- Search by device name or Tailscale IP
- One-click copy for device IP addresses
- Per-device `tailscale ping`
- Lightweight traffic and ping history display
- Compact GTK layout that feels like a utility panel

## Why It Exists

Because sometimes you do not want a whole giant settings flow.
Sometimes you just want a little window that says:

`is tailscale on?`

and then lets you poke a device.

## Requirements

- Linux
- Python 3
- GTK 3 / PyGObject
- Tailscale installed and available in `PATH`
- `tailscaled` running

## Quick Start

Run the app with:

```bash
python3 App0.1.Py
```

If Tailscale status is unavailable, make sure the daemon is running:

```bash
sudo systemctl start tailscaled
```

If GTK fails to start, launch it from a graphical Linux session instead of a headless shell.

## Toggle Behavior

The in-app connect and disconnect button currently calls:

```bash
sudo -n tailscale up
sudo -n tailscale down
```

That means the toggle works best when your environment already allows those commands non-interactively.

## Project Layout

| Path | What it does |
| --- | --- |
| `App0.1.Py` | Main window, refresh flow, toggle logic, ping handling |
| `controller_page.py` | Home screen UI |
| `status_page.py` | Device list UI, search, copy IP, ping rows |
| `assets/` | Icons and image assets |

## Current Notes

- The project currently targets GTK 3
- The Sign Out button is present in the layout but is not wired up yet
- This repo is best thought of as a personal utility app and learning project

## Very Important Again

This is a fan-made side project.
It is not an official Tailscale GUI.
It is not supported by Tailscale.
It is just a nice little wrapper around the CLI made for fun.

## Disclaimer

Tailscale is the product this app talks to.
This repository is not an official Tailscale repository.
If something looks homemade, that is because it is homemade.
