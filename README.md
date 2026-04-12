<p align="center">
  <img src="tailscale_controller/assets/images/logo.png" alt="Tailscale Controller logo" width="104">
</p>

<h1 align="center">Tailscale Controller</h1>

<p align="center">
  A small unofficial GTK desktop controller for Tailscale on Linux.
</p>

<p align="center">
  <strong>Unofficial.</strong>
  <strong>Not affiliated with Tailscale.</strong>
  <strong>Built as a personal desktop utility.</strong>
</p>

---

> [!WARNING]
> This repository is not an official Tailscale project.
> It is not made by, endorsed by, or affiliated with Tailscale Inc.

## Overview

Tailscale Controller is a lightweight Python + GTK app that wraps the `tailscale` CLI in a compact desktop window.
It is designed for quick checks, quick toggles, and quick access to device information without living in a terminal.

The app currently includes:

- A controller page with a large on/off toggle
- A status page for your local device and peer devices
- Search by device name or Tailscale IP
- Per-device `tailscale ping`
- One-click copy for the primary Tailscale IP
- Lightweight traffic display using current tx/rx counters
- An account page with live sign-in state detection
- Sign-in and sign-out actions that call the Tailscale CLI
- A sign-in popup with the returned login link and a copy button

## Requirements

- Linux
- Python 3
- GTK 3 with PyGObject
- Tailscale installed and available in `PATH`
- A graphical session

The app shells out to the `tailscale` CLI, so it will not work correctly if the command is missing.

## Running The App

Start the app with:

```bash
python3 -m tailscale_controller
```

If GTK cannot initialize, make sure you are launching it from a graphical desktop session.

If Tailscale status cannot be read, verify that Tailscale is installed and running on the machine.

## How It Works

### Controller Page

The home page shows the current backend state and a large toggle button.
The window is intentionally fixed-size and docks near the bottom-right of the screen like a utility panel.

The app refreshes Tailscale status automatically every 5 seconds.
Pressing `Esc` closes the app from the controller page, or returns to the controller page from the other views.

### Status Page

The status page loads:

- Your local device
- Peer devices from `tailscale status --json`
- Presence state: online, idle, or offline
- Primary Tailscale IP
- Relay information when available
- Basic traffic counters
- Last-seen text for offline devices

From each device row you can:

- Copy the primary Tailscale IP
- Run `tailscale ping` against that device
- Search the current list by name or IP
- Clear saved ping results and reset traffic baselines

### Account Page

The account page shows whether the local device appears signed in based on the Tailscale backend state and keeps the small account indicator on the controller page in sync.

From the account page you can:

- Sign in with `tailscale login`
- Sign out with `tailscale logout`
- Confirm an admin-permission prompt before privileged actions run
- See the returned sign-in link in a popup window
- Copy the sign-in link directly from that popup

## Commands Used

This app currently depends on these CLI calls:

```bash
tailscale status --json
tailscale ping --c 1 --until-direct=false <target>
tailscale login --timeout=5s
tailscale logout
sudo -n tailscale up
sudo -n tailscale down
```

## Toggle Permissions

The main connect/disconnect button uses:

```bash
sudo -n tailscale up
sudo -n tailscale down
```

Because of that, toggling works best when your environment already allows those commands without prompting for a password.

If `sudo -n` is not allowed, the app will still open, but the toggle action may fail with a permissions message.

## Account Permissions

The account page uses privileged `tailscale login` and `tailscale logout` commands.

Before those actions run, the app shows a small warning dialog explaining that admin permission is needed.
When available, the app prefers a graphical PolicyKit prompt via `pkexec`; otherwise it falls back to `sudo`.

After `tailscale login` starts, the app opens a sign-in popup that shows the login URL when one is returned, along with a copy button.

## Project Layout

| Path | Purpose |
| --- | --- |
| `tailscale_controller/` | Main Python package for the app |
| `tailscale_controller/app.py` | Main window, background refresh, toggle logic, account-state checks, ping handling |
| `tailscale_controller/controller_page.py` | Home/controller page UI |
| `tailscale_controller/status_page.py` | Device list UI, search, copy IP, ping row actions |
| `tailscale_controller/account_page.py` | Account page UI and account action controls |
| `pyproject.toml` | Packaging metadata and console entry point |
| `GITHUB_SETUP.md` | Extra repository setup notes |

## Current Limitations

- Linux only
- GTK 3 only
- Depends on the local `tailscale` CLI rather than a native API
- Connect/disconnect requires suitable `sudo` access
- Account actions still depend on local CLI and desktop auth tooling
- No packaging or installer is included yet

## Disclaimer

This is a fan-made side project and learning project.
It is not an official Tailscale GUI and is not supported by Tailscale.
