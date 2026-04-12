# Load GTK for this page UI
import os
from pathlib import Path

import gi

# Tell Python we are using GTK 3
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk


# Status page that shows devices and ping results
class StatusPage(Gtk.Box):

    ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "images"
    UI_ICONS_DIR = ASSETS_DIR / "ui-icons"
    OS_ICONS_DIR = ASSETS_DIR / "os-icons"
    BUTTON_LABEL_RESET_DELAY_MS = 900

    def __init__(self, app):
        # Build this page as a vertical layout
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # Keep a reference to the main app so this page can use shared logic
        self.app = app
        self.all_devices = []
        self.backend_state = "unknown"
        self._toolbar_icon_cache = {}
        self._os_icon_cache = {}

        # Add small CSS helpers for temporary Ping button flashes
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(
            b"""
            button.ping-success {
                background-image: none;
                background-color: #1f8f4c;
                color: #ffffff;
            }

            button.ping-failure {
                background-image: none;
                background-color: #b03a2e;
                color: #ffffff;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        toolbar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        toolbar_box.set_border_width(4)
        self.pack_start(toolbar_box, False, False, 0)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar_box.pack_start(top_row, False, False, 0)

        left_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        top_row.pack_start(left_column, True, True, 0)

        right_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        top_row.pack_end(right_column, False, False, 0)

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        left_column.pack_start(title_row, False, False, 0)

        # Go back to the controller page
        back_button = Gtk.Button(label="Back")
        back_button.connect("clicked", self.app.on_back_clicked)
        title_row.pack_start(back_button, False, False, 0)

        # Title for the status page
        title_label = Gtk.Label()
        title_label.set_markup("<b>Status</b>")
        title_label.set_xalign(0)
        title_row.pack_start(title_label, False, False, 0)

        self.search_button = Gtk.Button()
        self.search_button.set_relief(Gtk.ReliefStyle.NONE)
        self.search_button.set_tooltip_text("Search")
        self.search_button.set_image(self.build_toolbar_icon("search.svg"))
        self.search_button.connect("clicked", self.on_search_button_clicked)
        title_row.pack_start(self.search_button, False, False, 0)

        self.search_revealer = Gtk.Revealer()
        self.search_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        self.search_revealer.set_transition_duration(180)
        title_row.pack_start(self.search_revealer, False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search name or IP")
        self.search_entry.set_width_chars(22)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("stop-search", self.on_stop_search)
        self.search_revealer.add(self.search_entry)

        # Short summary text like backend state and device count
        self.status_summary_label = self.make_label("Loading devices...")
        left_column.pack_start(self.status_summary_label, False, False, 0)

        # Error text shown when status loading fails
        self.status_error_label = self.make_label("", wrap=True)
        left_column.pack_start(self.status_error_label, False, False, 0)
        self.status_error_label.set_no_show_all(True)
        self.status_error_label.hide()

        # Manually refresh device data
        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.connect("clicked", self.app.on_refresh_status_clicked)
        right_column.pack_start(self.refresh_button, False, False, 0)

        # Clear all saved ping results
        self.clear_ping_button = Gtk.Button(label="Clear")
        self.clear_ping_button.connect("clicked", self.app.on_clear_ping_history_clicked)
        right_column.pack_start(self.clear_ping_button, False, False, 0)

        self.refresh_button.show()

        # Scroll area so long device lists still fit
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.pack_start(scroller, True, True, 0)

        # Box that holds all of the device rows
        self.devices_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.devices_box.set_border_width(4)
        scroller.add(self.devices_box)

    def make_label(self, text="", xalign=0, wrap=False):
        # Small helper so labels are created the same way each time
        label = Gtk.Label(label=text)
        label.set_xalign(xalign)
        label.set_line_wrap(wrap)
        return label

    def make_markup_label(self, markup="", xalign=0):
        # Helper for labels that use color or bold markup
        label = Gtk.Label()
        label.set_markup(markup)
        label.set_xalign(xalign)
        return label

    def build_toolbar_icon(self, icon_name):
        # Load small toolbar artwork from the shared UI icon folder
        pixbuf = self.load_cached_pixbuf(self.UI_ICONS_DIR / icon_name, 16, 16)
        if pixbuf is not None:
            return Gtk.Image.new_from_pixbuf(pixbuf)

        return Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.MENU)

    def get_status_indicator_markup(self, device):
        # Build a colored circle for the device state
        presence = self.app.get_device_presence(device)

        if presence == "online":
            color = "#1DB954"
            tooltip = "Online"
        elif presence == "idle":
            color = "#F39C12"
            tooltip = "Idle"
        else:
            color = "#D64541"
            tooltip = "Offline"

        return f'<span foreground="{color}" size="large">●</span> <span>{tooltip}</span>'

    def get_os_icon_name(self, device):
        # Map device OS names to simple built-in themed icons
        os_name = str(device.get("OS", "")).lower()

        if "linux" in os_name:
            return "computer-symbolic"
        if "windows" in os_name:
            return "computer-symbolic"
        if "mac" in os_name or "darwin" in os_name:
            return "computer-symbolic"
        if "android" in os_name:
            return "smartphone-symbolic"
        if "ios" in os_name or "iphone" in os_name or "ipad" in os_name:
            return "smartphone-symbolic"

        return "network-workgroup-symbolic"

    def build_os_icon(self, device):
        # Use a custom image when available, otherwise fall back to themed icons
        os_name = str(device.get("OS", "")).lower()
        icon_path = None

        if "linux" in os_name:
            icon_path = self.OS_ICONS_DIR / "Linux.png"
        elif "windows" in os_name:
            icon_path = self.OS_ICONS_DIR / "Windows.png"
        elif "android" in os_name:
            icon_path = self.OS_ICONS_DIR / "android.svg"

        pixbuf = self.load_cached_pixbuf(icon_path, 16, 16)
        if pixbuf is not None:
            return Gtk.Image.new_from_pixbuf(pixbuf)

        return Gtk.Image.new_from_icon_name(
            self.get_os_icon_name(device),
            Gtk.IconSize.MENU
        )

    def load_cached_pixbuf(self, icon_path, width, height):
        # Reuse small scaled artwork so repeated refreshes do not keep hitting disk
        if icon_path is None:
            return None

        icon_path = os.fspath(icon_path)
        cache_key = (icon_path, width, height)
        if cache_key in self._os_icon_cache:
            return self._os_icon_cache[cache_key]

        if cache_key in self._toolbar_icon_cache:
            return self._toolbar_icon_cache[cache_key]

        if not os.path.exists(icon_path):
            return None

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                icon_path,
                width=width,
                height=height,
                preserve_aspect_ratio=True
            )
        except GLib.Error:
            return None

        cache = (
            self._toolbar_icon_cache
            if icon_path.startswith(os.fspath(self.UI_ICONS_DIR))
            else self._os_icon_cache
        )
        cache[cache_key] = pixbuf
        return pixbuf

    def get_device_ip(self, device):
        # Pick the first Tailscale IP for the Copy IP button
        ip_addresses = device.get("TailscaleIPs") or []
        if ip_addresses:
            return ip_addresses[0]
        return ""

    def on_copy_ip_clicked(self, button, ip_address):
        # Copy the device IP and show quick feedback on the button
        if not ip_address:
            button.set_label("No IP")
            GLib.timeout_add(self.BUTTON_LABEL_RESET_DELAY_MS, self.reset_button_label, button, "Copy IP")
            return

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(ip_address, -1)
        clipboard.store()
        button.set_label("Copied!")
        GLib.timeout_add(self.BUTTON_LABEL_RESET_DELAY_MS, self.reset_button_label, button, "Copy IP")

    def reset_button_label(self, button, text):
        # Restore a temporary button label
        button.set_label(text)
        return False

    def set_summary(self, text):
        # Update the summary line near the top of the page
        self.status_summary_label.set_text(text)

    def set_error(self, text):
        # Update the error message area
        self.status_error_label.set_text(text)
        if text.strip():
            self.status_error_label.show()
        else:
            self.status_error_label.hide()

    def clear_devices(self):
        # Remove all current device rows before rebuilding the list
        for child in self.devices_box.get_children():
            self.devices_box.remove(child)

    def on_search_button_clicked(self, button):
        # Toggle the inline search box beside the search button
        is_visible = self.search_revealer.get_reveal_child()
        self.search_revealer.set_reveal_child(not is_visible)

        if is_visible:
            self.search_entry.set_text("")
        else:
            self.search_entry.grab_focus()

    def on_search_changed(self, entry):
        # Filter the current device list as the user types
        self.refresh_device_list()

    def on_stop_search(self, entry):
        # Escape clears and hides the search box
        entry.set_text("")
        self.search_revealer.set_reveal_child(False)
        return True

    def get_search_query(self):
        # Keep search text normalized in one place
        if not self.search_revealer.get_reveal_child():
            return ""
        return self.search_entry.get_text().strip().lower()

    def device_matches_search(self, device):
        # Match against the device name or any listed Tailscale IP
        query = self.get_search_query()
        if not query:
            return True

        device_name = self.app.get_device_name(device).lower()
        if query in device_name:
            return True

        for ip_address in device.get("TailscaleIPs") or []:
            if query in str(ip_address).lower():
                return True

        return False

    def get_filtered_devices(self):
        # Return only devices that match the active search query
        return [device for device in self.all_devices if self.device_matches_search(device)]

    def set_device_data(self, backend_state, devices):
        # Cache the latest fetched device data so search can filter it locally
        self.backend_state = backend_state
        self.all_devices = list(devices)
        self.refresh_device_list()

    def clear_device_data(self, empty_message="No devices found in Tailscale status."):
        # Drop cached device rows when the backend cannot provide data
        self.backend_state = "unknown"
        self.all_devices = []
        self.clear_devices()
        self.show_empty_message(empty_message)

    def refresh_device_list(self):
        # Rebuild the visible rows using the current search filter
        filtered_devices = self.get_filtered_devices()
        self.clear_devices()
        self.set_summary(
            f"Backend: {self.backend_state} | Devices shown: {len(filtered_devices)} / {len(self.all_devices)}"
        )

        if not self.all_devices:
            self.show_empty_message("No devices found in Tailscale status.")
            return

        if not filtered_devices:
            self.show_empty_message("No devices match that search.")
            return

        for device in filtered_devices:
            self.add_device_row(device)

    def show_empty_message(self, text):
        # Show a simple message when there are no devices to display
        self.devices_box.pack_start(self.make_label(text), False, False, 0)
        self.devices_box.show_all()

    def add_device_row(self, device):
        # Build one device card and add it to the page
        self.devices_box.pack_start(self.build_device_row(device), False, False, 0)
        self.devices_box.show_all()

    def build_device_row(self, device):
        # Pull the values this row needs from the shared app logic
        try:
            device_key = self.app.get_device_key(device)
            device_name = self.app.get_device_name(device)
            device_ip = self.get_device_ip(device)
            ping_target = self.app.get_ping_target(device)
            ping_text = self.app.ping_results.get(device_key, "No ping run yet.")
            presence = self.app.get_device_presence(device)
            is_pinging = device_key in self.app.pinging_devices
            flash_state = self.app.ping_flash_states.get(device_key)

            # Outer frame so each device looks like its own card
            row_frame = Gtk.Frame()

            row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            row_box.set_border_width(10)
            row_frame.add(row_box)

            # Top row holds the device name and the Ping button
            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row_box.pack_start(top_row, False, False, 0)

            # Show the device name with a status word and colored dot
            section_title = device.get("_section_title", "Device")
            name_label = self.make_label(f"{section_title}: {device_name}")
            top_row.pack_start(name_label, True, True, 0)

            status_label = self.make_markup_label(self.get_status_indicator_markup(device))
            top_row.pack_start(status_label, False, False, 0)

            # Copy the device IP straight to the clipboard
            copy_ip_button = Gtk.Button(label="Copy IP")
            copy_ip_button.set_sensitive(bool(device_ip))
            copy_ip_button.connect("clicked", self.on_copy_ip_clicked, device_ip)
            top_row.pack_start(copy_ip_button, False, False, 0)

            # Ping just this device from the row
            ping_button = Gtk.Button(label="Ping")
            ping_button.set_sensitive(bool(ping_target) and presence != "offline" and not is_pinging)
            if flash_state == "success":
                ping_button.get_style_context().add_class("ping-success")
            elif flash_state == "failure":
                ping_button.get_style_context().add_class("ping-failure")
            ping_button.connect("clicked", self.app.on_ping_clicked, device)
            top_row.pack_start(ping_button, False, False, 0)

            # Show an OS icon beside the extra information line
            details_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.pack_start(details_row, False, False, 0)

            os_icon = self.build_os_icon(device)
            details_row.pack_start(os_icon, False, False, 0)

            details_label = self.make_label(self.app.format_device_details(device), wrap=True)
            details_row.pack_start(details_label, True, True, 0)

            last_online_text = self.app.format_last_online(device)
            if last_online_text:
                last_online_label = self.make_label(last_online_text, xalign=1)
                details_row.pack_end(last_online_label, False, False, 0)

            # Show the most recent ping result for this device
            ping_label = self.make_label(f"Ping: {ping_text}", wrap=True)
            row_box.pack_start(ping_label, False, False, 0)

            return row_frame
        except Exception as error:
            # Fall back to a simple row so one bad device cannot blank the whole list
            fallback_frame = Gtk.Frame()
            fallback_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            fallback_box.set_border_width(10)
            fallback_frame.add(fallback_box)
            fallback_box.pack_start(
                self.make_label(f'{device.get("_section_title", "Device")}: {self.app.get_device_name(device)}', wrap=True),
                False,
                False,
                0
            )
            fallback_box.pack_start(
                self.make_label(f"Row render error: {error}", wrap=True),
                False,
                False,
                0
            )
            return fallback_frame
