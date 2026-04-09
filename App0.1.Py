# Load JSON so we can read structured data from `tailscale status --json`
from datetime import datetime, timezone
import json
from pathlib import Path

# Run Tailscale terminal commands from Python
import subprocess
import threading

# Load GTK / GLib for the desktop app UI
import gi

# Tell Python we are using GTK 3
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

# Import the page classes
from account_page import AccountPage
from controller_page import ControllerPage
from status_page import StatusPage

APP_DIR = Path(__file__).resolve().parent


class TailscaleApp(Gtk.Window):

    ASSETS_DIR = APP_DIR / "assets" / "images"
    LOGO_ICON_PATH = ASSETS_DIR / "logo.png"
    TOGGLE_ON_ICON_PATH = ASSETS_DIR / "OnOf-Icons" / "TurnOn.svg"
    TOGGLE_OFF_ICON_PATH = ASSETS_DIR / "OnOf-Icons" / "TurnOff.svg"
    CONTROLLER_MIN_WIDTH = 336
    CONTROLLER_MIN_HEIGHT = 404
    ACCOUNT_MIN_WIDTH = 360
    ACCOUNT_MIN_HEIGHT = 170
    STATUS_MIN_WIDTH = 608
    STATUS_MIN_HEIGHT = 560
    TASKBAR_DOCK_MARGIN = 12
    STATUS_COMMAND_TIMEOUT_SECONDS = 8
    TOGGLE_COMMAND_TIMEOUT_SECONDS = 20

    def __init__(self):
        super().__init__(title="Tailscale Controller")

        self.set_border_width(8)

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(False)
        self.set_skip_pager_hint(False)
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        if self.LOGO_ICON_PATH.exists():
            self.set_icon_from_file(str(self.LOGO_ICON_PATH))
        self.get_style_context().add_class("tailscale-window")

        # Add a small custom style layer so the front page feels more polished
        self.install_css()

        # Track whether Tailscale is currently connected
        self.is_connected = False

        # Surface lightweight home-screen guidance and errors
        self.controller_notice = ""
        self.controller_notice_is_error = False

        # Remember the latest ping result for each device
        self.ping_results = {}

        # Store traffic baselines so Clear can reset tx/rx from "now"
        self.traffic_baselines = {}

        # Track devices that are currently being pinged
        self.pinging_devices = set()

        # Track short-lived ping flash colors for the button UI
        self.ping_flash_states = {}
        self.ping_flash_tokens = {}
        self.status_refresh_token = 0
        self.status_refresh_in_progress = False
        self.pending_status_refresh_include_controller = False
        self.toggle_in_progress = False
        self.account_status_check_in_progress = False
        self.account_sign_in_state = "unknown"

        # Gtk.Stack lets us swap between pages in the same window
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(250)

        # Add the page stack directly so the window does not draw an extra outer box
        self.add(self.stack)

        # Build both pages and add them to the stack
        self.controller_page = ControllerPage(self)
        self.account_page = AccountPage(self)
        self.status_page = StatusPage(self)
        self.stack.add_named(self.controller_page, "controller")
        self.stack.add_named(self.account_page, "account")
        self.stack.add_named(self.status_page, "status")
        self.stack.set_visible_child_name("controller")

        # Check status once at startup
        self.update_status()
        GLib.idle_add(self.lock_to_page_size, "controller")

        # Re-check status automatically every 5 seconds
        GLib.timeout_add(5000, self.auto_refresh_status)
        GLib.timeout_add(3000, self.auto_refresh_account_status)

        # Small keyboard shortcuts help this act more like a utility panel
        self.connect("key-press-event", self.on_key_press_event)

    def install_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(
            b"""
            .tailscale-window {
                background-image: none;
                background-color: #11161d;
            }

            .home-shell {
                border-radius: 18px;
                border: 1px solid rgba(130, 160, 190, 0.16);
                background-image: linear-gradient(180deg, #1d2630 0%, #121920 100%);
                box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
            }

            .hero-title {
                color: #f4f7fb;
            }

            .hero-kicker {
                color: #8ebdff;
            }

            .hero-subtitle {
                color: #97a9bc;
            }

            .hero-caption {
                color: #7f93a8;
            }

            button.hero-toggle {
                background-image: linear-gradient(180deg, #273342 0%, #1b2430 100%);
                border-radius: 22px;
                border: 1px solid rgba(143, 176, 210, 0.14);
                box-shadow: 0 8px 22px rgba(0, 0, 0, 0.28);
                padding: 14px;
            }

            button.hero-toggle:hover {
                background-image: linear-gradient(180deg, #314054 0%, #212c3a 100%);
            }

            button.panel-button {
                background-image: none;
                background-color: #202b37;
                border-radius: 14px;
                border: 1px solid rgba(143, 176, 210, 0.14);
                color: #eaf2fb;
                padding: 10px 12px;
            }

            button.panel-button:hover {
                background-image: none;
                background-color: #2a3746;
            }

            button.signout-button {
                background-image: none;
                background-color: rgba(214, 69, 65, 0.14);
                color: #ffb6b0;
                border-radius: 12px;
                border: 1px solid rgba(214, 69, 65, 0.22);
                padding: 8px 12px;
            }

            """
        )
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def run_command(self, command, timeout=None):
        # Run a terminal command and always return the result in one place
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )

    def run_in_background(self, target, *args):
        # Keep shell work off the GTK thread so the window stays responsive
        worker = threading.Thread(target=target, args=args, daemon=True)
        worker.start()
        return worker

    def fetch_tailscale_data(self):
        # Run the JSON version of tailscale status so the data is easier to use
        try:
            result = self.run_command(
                ["tailscale", "status", "--json"],
                timeout=self.STATUS_COMMAND_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": "Timed out while checking Tailscale status.",
                "data": None,
            }
        except FileNotFoundError:
            return {
                "ok": False,
                "error": "The `tailscale` command was not found on this system.",
                "data": None,
            }
        except Exception as error:
            return {
                "ok": False,
                "error": f"Error checking status: {error}",
                "data": None,
            }

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # If Tailscale returned an error, pass that error back to the UI
        if result.returncode != 0:
            message = stderr or stdout or "Unknown error while running tailscale status --json."
            return {
                "ok": False,
                "error": message,
                "data": None,
            }

        # Turn the JSON text into a Python dictionary
        try:
            parsed = json.loads(stdout or "{}")
        except json.JSONDecodeError as error:
            return {
                "ok": False,
                "error": f"Failed to parse Tailscale status JSON: {error}",
                "data": None,
            }

        return {
            "ok": True,
            "error": "",
            "data": parsed,
        }

    def get_connection_state(self, data):
        # Decide if the main toggle should treat Tailscale as connected
        backend_state = str(data.get("BackendState", "")).lower()
        disconnected_states = {"", "stopped", "needslogin"}
        return backend_state not in disconnected_states

    def get_device_name(self, device):
        # Pick a short, user-facing name and avoid raw IPs where possible
        candidates = [
            device.get("DisplayName"),
            device.get("ComputedName"),
            device.get("Name"),
            self.get_short_dns_name(device),
            device.get("HostName"),
            device.get("DNSName", "").rstrip("."),
        ]

        for candidate in candidates:
            normalized_name = self.normalize_device_name(candidate)
            if normalized_name:
                return normalized_name

        return "Unknown device"

    def get_short_dns_name(self, device):
        # Convert a full tailnet DNS name into the short device label
        dns_name = str(device.get("DNSName", "")).rstrip(".")
        if not dns_name:
            return ""
        return dns_name.split(".", 1)[0]

    def normalize_device_name(self, value):
        # Clean up candidate names and reject raw IP addresses as labels
        text = str(value or "").strip()
        if not text:
            return ""

        if self.looks_like_ip_address(text):
            return ""

        return text

    def looks_like_ip_address(self, value):
        # Keep raw IPs out of the main device-name label
        parts = str(value).split(".")
        if len(parts) != 4:
            return False

        for part in parts:
            if not part.isdigit():
                return False
            number = int(part)
            if number < 0 or number > 255:
                return False

        return True

    def get_ping_target(self, device):
        # Choose the best value to use with `tailscale ping`
        dns_name = device.get("DNSName", "").rstrip(".")
        if dns_name:
            return dns_name

        host_name = device.get("HostName")
        if host_name:
            return host_name

        ip_addresses = device.get("TailscaleIPs") or []
        if ip_addresses:
            return ip_addresses[0]

        return None

    def get_device_key(self, device):
        # Create a stable key so we can remember ping results per device
        return (
            device.get("ID")
            or device.get("StableID")
            or device.get("PublicKey")
            or self.get_ping_target(device)
            or self.get_device_name(device)
        )

    def get_device_presence(self, device):
        # Convert the device state into one simple UI status
        if not device.get("Online"):
            return "offline"

        # Some Tailscale builds include extra activity hints, so treat those as idle
        if device.get("Idle") or device.get("IsIdle"):
            return "idle"

        return "online"

    def get_controller_presence(self, data):
        # Convert the main backend state into one home-page status
        backend_state = str(data.get("BackendState", "")).lower()

        if backend_state in {"", "stopped", "needslogin"}:
            return "offline"

        if backend_state in {"starting", "idle"}:
            return "idle"

        return "online"

    def get_presence_display(self, presence):
        # Shared UI text and color for presence states
        if presence == "online":
            return {
                "label": "Online",
                "color": "#1DB954",
            }

        if presence == "idle":
            return {
                "label": "Idle",
                "color": "#F39C12",
            }

        return {
            "label": "Offline",
            "color": "#D64541",
        }

    def format_device_traffic(self, device):
        # Keep traffic formatting in one place
        tx_bytes = device.get("TxBytes")
        rx_bytes = device.get("RxBytes")

        if tx_bytes is None or rx_bytes is None:
            return ""

        device_key = self.get_device_key(device)
        baseline = self.traffic_baselines.get(device_key, {"tx": 0, "rx": 0})

        display_tx = max(0, tx_bytes - baseline["tx"])
        display_rx = max(0, rx_bytes - baseline["rx"])

        return f"tx {self.format_bytes(display_tx)} / rx {self.format_bytes(display_rx)}"

    def format_bytes(self, value):
        # Turn raw byte counts into easier-to-read units
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(value)

        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024

    def format_device_details(self, device):
        # Build a short line of helpful extra info for the UI
        details = []

        ip_addresses = device.get("TailscaleIPs") or []
        if ip_addresses:
            details.append(ip_addresses[0])

        relay = device.get("Relay")
        if relay:
            details.append(f"relay: {relay}")

        traffic = self.format_device_traffic(device)
        if traffic:
            details.append(traffic)

        return " | ".join(details) if details else "No extra details available."

    def format_last_online(self, device):
        # Show a short "last online" hint for offline or idle devices when available
        if device.get("Online"):
            return ""

        last_seen_text = str(device.get("LastSeen") or "").strip()
        if not last_seen_text:
            return "Last online unknown"

        try:
            normalized_text = last_seen_text.replace("Z", "+00:00")
            last_seen = datetime.fromisoformat(normalized_text)
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
        except (ValueError, OverflowError):
            return "Last online unknown"

        try:
            delta = datetime.now(timezone.utc) - last_seen.astimezone(timezone.utc)
            total_seconds = max(0, int(delta.total_seconds()))
        except (ValueError, OverflowError, OSError):
            return "Last online unknown"

        if total_seconds < 60:
            return "Last online just now"
        if total_seconds < 3600:
            minutes = total_seconds // 60
            return f"Last online {minutes}m ago"
        if total_seconds < 86400:
            hours = total_seconds // 3600
            return f"Last online {hours}h ago"
        if total_seconds < 604800:
            days = total_seconds // 86400
            return f"Last online {days}d ago"

        try:
            return f"Last online {last_seen.astimezone().strftime('%d %b')}"
        except (ValueError, OverflowError, OSError):
            return "Last online unknown"

    def extract_devices(self, data):
        # Turn the JSON into one simple list of devices to display
        devices = []

        # Add the local machine first
        local_device = data.get("Self")
        if isinstance(local_device, dict) and local_device:
            local_copy = dict(local_device)
            local_copy["_section_title"] = "This Device"
            devices.append(local_copy)

        # Add all peer devices after that
        peers = data.get("Peer") or {}
        if isinstance(peers, dict):
            for peer in peers.values():
                if isinstance(peer, dict):
                    peer_copy = dict(peer)
                    peer_copy["_section_title"] = "Peer"
                    devices.append(peer_copy)

        return devices

    def render_status_page(self, fetch_result):
        # Redraw the status page using the latest fetched data
        # Show the error message if status loading failed
        if not fetch_result["ok"]:
            self.status_page.set_summary("Unable to load Tailscale devices.")
            self.status_page.set_error(fetch_result["error"])
            self.status_page.clear_device_data("Unable to load the device list.")
            return

        # Pull useful values out of the fetched JSON
        data = fetch_result["data"]
        devices = self.extract_devices(data)
        backend_state = data.get("BackendState", "unknown")

        self.status_page.set_error("")
        self.status_page.set_device_data(backend_state, devices)

    def set_controller_notice(self, message="", is_error=False):
        # Keep short home-page guidance in one place
        self.controller_notice = message.strip()
        self.controller_notice_is_error = is_error

    def clear_controller_notice(self):
        # Remove any temporary home-page message
        self.controller_notice = ""
        self.controller_notice_is_error = False

    def update_status(self):
        # Fetch fresh Tailscale data in the background for both pages
        self.request_status_refresh(include_controller=True)

    def auto_refresh_status(self):
        # Called by GLib every 5 seconds
        self.update_status()
        return True

    def auto_refresh_account_status(self):
        # Poll account status regularly so the home-page account indicator stays fresh
        self.check_account_status()
        return True

    def request_status_refresh(self, include_controller):
        # Coalesce refresh requests so slow backend calls do not pile up background threads
        self.pending_status_refresh_include_controller = (
            self.pending_status_refresh_include_controller or include_controller
        )

        if self.status_refresh_in_progress:
            return

        include_controller = self.pending_status_refresh_include_controller
        self.pending_status_refresh_include_controller = False
        self.status_refresh_token += 1
        refresh_token = self.status_refresh_token
        self.status_refresh_in_progress = True
        self.run_in_background(self.fetch_status_in_background, refresh_token, include_controller)

    def fetch_status_in_background(self, refresh_token, include_controller):
        # Run one backend status fetch and marshal the UI update back to GTK
        fetch_result = self.fetch_tailscale_data()
        GLib.idle_add(
            self.apply_status_refresh_result,
            refresh_token,
            include_controller,
            fetch_result
        )

    def apply_status_refresh_result(self, refresh_token, include_controller, fetch_result):
        self.status_refresh_in_progress = False

        # Ignore late results from older background refreshes
        if refresh_token != self.status_refresh_token:
            if self.pending_status_refresh_include_controller:
                GLib.idle_add(
                    self.request_status_refresh,
                    self.pending_status_refresh_include_controller
                )
            return False

        if include_controller:
            controller_presence = "offline"
            if fetch_result["ok"]:
                self.is_connected = self.get_connection_state(fetch_result["data"])
                controller_presence = self.get_controller_presence(fetch_result["data"])
            else:
                self.is_connected = False

            # Update the main controller page text/buttons
            presence_display = self.get_presence_display(controller_presence)
            button_icon = (
                self.TOGGLE_ON_ICON_PATH
                if self.is_connected
                else self.TOGGLE_OFF_ICON_PATH
            )

            self.controller_page.state_badge_label.set_markup(
                f'<span foreground="{presence_display["color"]}" size="large">●</span> '
                f'<span size="large"><b>{presence_display["label"]}</b></span>'
            )
            self.controller_page.set_toggle_button_icon(button_icon)
            if not fetch_result["ok"]:
                self.controller_page.set_subtitle_text("Desktop control panel")
                self.controller_page.set_home_message(fetch_result["error"])
            else:
                self.controller_page.set_subtitle_text("Desktop control panel")
                self.controller_page.set_home_message(
                    self.controller_notice or "Manufactured by Mushy"
                )

        self.render_status_page(fetch_result)
        self.relock_visible_page()

        if self.pending_status_refresh_include_controller:
            GLib.idle_add(
                self.request_status_refresh,
                self.pending_status_refresh_include_controller
            )
        return False

    def refresh_status_page(self):
        # Refresh only the status page without repainting the home view
        self.request_status_refresh(include_controller=False)

    def relock_visible_page(self):
        # Re-apply the fixed size and dock position after async UI updates settle
        visible_page = self.stack.get_visible_child_name() or "controller"
        GLib.idle_add(self.lock_to_page_size, visible_page)

    def lock_to_page_size(self, page_name):
        # Keep each page on a fixed size that matches its layout
        if page_name == "status":
            page = self.status_page
            minimum_width = self.STATUS_MIN_WIDTH
            minimum_height = self.STATUS_MIN_HEIGHT
            width_padding = 0
            height_padding = 0
        elif page_name == "account":
            page = self.account_page
            minimum_width = self.ACCOUNT_MIN_WIDTH
            minimum_height = self.ACCOUNT_MIN_HEIGHT
            width_padding = 0
            height_padding = 0
        else:
            page = self.controller_page
            minimum_width = self.CONTROLLER_MIN_WIDTH
            minimum_height = self.CONTROLLER_MIN_HEIGHT
            width_padding = 0
            height_padding = 0

        page.show()
        minimum, natural = page.get_preferred_size()
        target_width = max(natural.width + width_padding, minimum_width)
        target_height = max(natural.height + height_padding, minimum_height)

        geometry = Gdk.Geometry()
        geometry.min_width = target_width
        geometry.max_width = target_width
        geometry.min_height = target_height
        geometry.max_height = target_height

        self.set_geometry_hints(
            None,
            geometry,
            Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE
        )
        self.set_default_size(target_width, target_height)
        self.resize(target_width, target_height)
        self.set_resizable(False)
        self.dock_to_taskbar_edge(target_width, target_height)
        return False

    def dock_to_taskbar_edge(self, width, height):
        # Sit the window in the bottom-right work area so it hugs the taskbar edge
        screen = self.get_screen() or Gdk.Screen.get_default()
        if screen is None:
            return

        monitor_index = screen.get_primary_monitor()
        if monitor_index < 0:
            monitor_index = 0

        workarea = screen.get_monitor_workarea(monitor_index)
        target_x = workarea.x + workarea.width - width - self.TASKBAR_DOCK_MARGIN
        target_y = workarea.y + workarea.height - height - self.TASKBAR_DOCK_MARGIN
        self.move(target_x, target_y)

    def on_key_press_event(self, widget, event):
        # Escape behaves like closing a dock-style popup
        if event.keyval == Gdk.KEY_Escape:
            if self.stack.get_visible_child_name() == "controller":
                self.close()
            else:
                self.on_back_clicked(None)
            return True
        return False

    def on_toggle_clicked(self, button):
        # Turn Tailscale off if it is on, or on if it is off
        if self.toggle_in_progress:
            return

        self.toggle_in_progress = True
        self.controller_page.toggle_button.set_sensitive(False)
        self.run_in_background(self.run_toggle_command_in_background)

    def run_toggle_command_in_background(self):
        # Run the privileged toggle command away from the GTK event loop
        try:
            command = (
                ["sudo", "-n", "tailscale", "down"]
                if self.is_connected
                else ["sudo", "-n", "tailscale", "up"]
            )
            result = self.run_command(command, timeout=self.TOGGLE_COMMAND_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            GLib.idle_add(
                self.finish_toggle_command,
                None,
                RuntimeError("Timed out while changing the Tailscale connection state.")
            )
            return
        except Exception as error:
            GLib.idle_add(self.finish_toggle_command, None, error)
            return

        GLib.idle_add(self.finish_toggle_command, result, None)

    def format_toggle_command_error(self, result):
        # Translate common sudo failures into a clearer home-page message
        message = (result.stderr or result.stdout).strip()
        lowered = message.lower()

        if (
            "password is required" in lowered
            or "a terminal is required" in lowered
            or "no tty present" in lowered
        ):
            return (
                "Sudo access is required to toggle Tailscale from this app. "
                "Run it from a terminal with sudo permission or allow passwordless sudo for tailscale."
            )

        return message or "Unable to change the Tailscale connection state."

    def finish_toggle_command(self, result, error):
        # Restore the toggle button and refresh the UI after the command finishes
        self.toggle_in_progress = False
        self.controller_page.toggle_button.set_sensitive(True)

        if error is not None:
            self.set_controller_notice(f"Unable to change Tailscale state: {error}", is_error=True)
            self.update_status()
            return False

        if result.returncode != 0:
            self.set_controller_notice(
                self.format_toggle_command_error(result),
                is_error=True
            )
        elif self.controller_notice_is_error:
            self.clear_controller_notice()

        self.update_status()
        return False

    def on_open_status_page_clicked(self, button):
        # Refresh first, then switch to the status page
        self.update_status()
        self.stack.set_visible_child_name("status")
        GLib.idle_add(self.lock_to_page_size, "status")

    def on_open_account_page_clicked(self, button):
        # Switch to the separate account page
        self.stack.set_visible_child_name("account")
        GLib.idle_add(self.lock_to_page_size, "account")
        self.check_account_status()

    def check_account_status(self):
        # Use tailscale status to decide whether the user appears to be signed in
        if self.account_status_check_in_progress:
            return

        self.account_status_check_in_progress = True
        self.run_in_background(self.check_account_status_in_background)

    def check_account_status_in_background(self):
        fetch_result = self.fetch_tailscale_data()
        GLib.idle_add(self.finish_account_status_check, fetch_result)

    def finish_account_status_check(self, fetch_result):
        self.account_status_check_in_progress = False

        if not fetch_result["ok"]:
            self.account_sign_in_state = "signed_out"
            self.controller_page.set_account_indicator(self.account_sign_in_state)
            self.account_page.set_account_status(
                f"Could not read Tailscale status: {fetch_result['error']}"
            )
            return False

        data = fetch_result["data"] or {}
        backend_state = str(data.get("BackendState", "")).lower()

        if backend_state in {"", "needslogin", "stopped"}:
            self.account_sign_in_state = "signed_out"
            self.controller_page.set_account_indicator(self.account_sign_in_state)
            self.account_page.set_account_status(
                "You are not signed in to Tailscale on this device."
            )
            return False

        self.account_sign_in_state = "signed_in"
        self.controller_page.set_account_indicator(self.account_sign_in_state)
        self.account_page.set_account_status(
            f"You appear to be signed in. Backend state: {backend_state or 'unknown'}."
        )
        return False

    def on_back_clicked(self, button):
        # Go back to the controller page
        self.update_status()
        self.stack.set_visible_child_name("controller")
        GLib.idle_add(self.lock_to_page_size, "controller")

    def on_refresh_status_clicked(self, button):
        # Manual refresh button for the status page
        self.update_status()

    def on_clear_ping_history_clicked(self, button):
        # Clear saved ping results and reset displayed traffic from the current values
        self.ping_results.clear()
        self.pinging_devices.clear()
        self.ping_flash_states.clear()
        self.ping_flash_tokens.clear()
        self.traffic_baselines.clear()
        self.status_page.refresh_device_list()
        self.run_in_background(self.refresh_ping_history_in_background)

    def refresh_ping_history_in_background(self):
        # Capture fresh traffic baselines without blocking the status page
        fetch_result = self.fetch_tailscale_data()
        GLib.idle_add(self.finish_refresh_ping_history, fetch_result)

    def finish_refresh_ping_history(self, fetch_result):
        # Apply the refreshed traffic baselines on the GTK thread
        if fetch_result["ok"]:
            for device in self.extract_devices(fetch_result["data"]):
                device_key = self.get_device_key(device)
                self.traffic_baselines[device_key] = {
                    "tx": device.get("TxBytes") or 0,
                    "rx": device.get("RxBytes") or 0,
                }
            self.render_status_page(fetch_result)
        else:
            self.status_page.set_error(fetch_result["error"])
            self.status_page.refresh_device_list()
        return False

    def flash_ping_button(self, device_key, flash_state):
        # Remember a temporary visual state for the Ping button
        flash_token = self.ping_flash_tokens.get(device_key, 0) + 1
        self.ping_flash_tokens[device_key] = flash_token
        self.ping_flash_states[device_key] = flash_state
        self.refresh_status_page()
        GLib.timeout_add(1200, self.clear_ping_flash_state, device_key, flash_token)

    def clear_ping_flash_state(self, device_key, flash_token):
        # Only clear the flash if this is still the latest one for the device
        if self.ping_flash_tokens.get(device_key) != flash_token:
            return False

        self.ping_flash_states.pop(device_key, None)
        self.refresh_status_page()
        return False

    def on_ping_clicked(self, button, device):
        # Run tailscale ping for the clicked device
        device_key = self.get_device_key(device)
        ping_target = self.get_ping_target(device)
        is_online = bool(device.get("Online"))

        # If we have nothing valid to ping, show that on the row
        if not ping_target:
            self.ping_results[device_key] = "No valid ping target for this device."
            self.refresh_status_page()
            return

        # Skip pinging devices that are currently offline
        if not is_online:
            self.ping_results[device_key] = "Device is offline, so ping was skipped."
            self.refresh_status_page()
            return

        # Ignore repeated clicks while the same device is already being pinged
        if device_key in self.pinging_devices:
            return

        self.pinging_devices.add(device_key)
        self.ping_results[device_key] = "Pinging..."
        self.refresh_status_page()
        self.run_in_background(self.run_ping_command_in_background, device_key, ping_target)

    def run_ping_command_in_background(self, device_key, ping_target):
        # Ask Tailscale to ping one device without freezing the GTK event loop
        try:
            result = self.run_command(
                ["tailscale", "ping", "--c", "1", "--until-direct=false", ping_target],
                timeout=10
            )
        except subprocess.TimeoutExpired:
            GLib.idle_add(self.finish_ping_command, device_key, None, "Ping timed out.", "failure")
            return
        except Exception as error:
            GLib.idle_add(self.finish_ping_command, device_key, None, f"Ping failed: {error}", "failure")
            return

        # Use the most useful command output as the saved result
        stdout = result.stdout.strip().splitlines()
        stderr = result.stderr.strip()

        if result.returncode == 0 and stdout:
            GLib.idle_add(self.finish_ping_command, device_key, stdout[-1], None, "success")
        elif stderr:
            GLib.idle_add(self.finish_ping_command, device_key, stderr, None, "failure")
        elif stdout:
            GLib.idle_add(self.finish_ping_command, device_key, stdout[-1], None, "success")
        else:
            GLib.idle_add(self.finish_ping_command, device_key, "Ping failed with no output.", None, "failure")

    def finish_ping_command(self, device_key, result_text, error_text, flash_state):
        # Save the ping result and repaint the row once the background command finishes
        if error_text:
            self.ping_results[device_key] = error_text
        else:
            self.ping_results[device_key] = result_text

        self.pinging_devices.discard(device_key)
        self.flash_ping_button(device_key, flash_state)
        return False


if __name__ == "__main__":
    initialized, _arguments = Gtk.init_check()
    if not initialized:
        raise SystemExit("Gtk couldn't be initialized. Make sure a graphical display is available.")

    # Create the window
    win = TailscaleApp()

    # Close GTK cleanly when the window is shut
    win.connect("destroy", Gtk.main_quit)

    # Show the UI
    win.show_all()

    # Start the GTK app loop
    Gtk.main()
