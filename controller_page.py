# Load GTK for this page UI
import os

import gi

# Tell Python we are using GTK 3
gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gtk


# Main controller page
class ControllerPage(Gtk.Box):

    def __init__(self, app):
        # Build this page as a vertical layout
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # Keep a reference to the main app so buttons can call shared logic
        self.app = app
        self.set_size_request(336, 404)

        # Center the main card on the page
        self.set_homogeneous(False)

        card_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.pack_start(card_wrapper, True, True, 0)

        # Styled shell for the main home panel without the default frame edge
        card_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card_frame.get_style_context().add_class("home-shell")
        card_wrapper.pack_start(card_frame, True, True, 0)

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_box.set_border_width(10)
        card_frame.add(card_box)

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        card_box.pack_start(header_row, False, False, 0)

        title_block = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header_row.pack_start(title_block, True, True, 0)

        pretitle_label = self.make_markup_label(
            "<span size='small'><b>UNOFFICIAL GUI</b></span>",
            xalign=0
        )
        pretitle_label.get_style_context().add_class("hero-kicker")
        title_block.pack_start(pretitle_label, False, False, 0)

        title_label = self.make_markup_label(
            "<span size='xx-large'><b>Tailscale</b></span>",
            xalign=0
        )
        title_label.get_style_context().add_class("hero-title")
        title_block.pack_start(title_label, False, False, 0)

        self.subtitle_label = self.make_label(
            "Desktop control panel",
            xalign=0,
            wrap=True
        )
        self.subtitle_label.get_style_context().add_class("hero-subtitle")
        title_block.pack_start(self.subtitle_label, False, False, 0)

        # Show a colored state badge above the main button
        self.state_badge_label = self.make_markup_label(
            '<span foreground="#999999">●</span> <span>Checking</span>',
            xalign=0.5,
            wrap=True
        )
        card_box.pack_start(self.state_badge_label, False, False, 0)

        # Main on/off button
        self.toggle_button = Gtk.Button()
        self.toggle_button.set_size_request(-1, 170)
        self.toggle_button.set_hexpand(True)
        self.toggle_button.set_relief(Gtk.ReliefStyle.NONE)
        self.toggle_button.get_style_context().add_class("hero-toggle")
        self.toggle_button.connect("clicked", self.app.on_toggle_clicked)
        toggle_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        toggle_row.set_hexpand(True)
        toggle_row.pack_start(self.toggle_button, True, True, 0)
        card_box.pack_start(toggle_row, False, False, 0)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        action_row.set_homogeneous(True)
        card_box.pack_start(action_row, False, False, 0)

        # Button that opens the live status page
        self.status_page_button = Gtk.Button(label="Status")
        self.status_page_button.get_style_context().add_class("panel-button")
        self.status_page_button.connect("clicked", self.app.on_open_status_page_clicked)
        action_row.pack_start(self.status_page_button, True, True, 0)

        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.get_style_context().add_class("panel-button")
        self.refresh_button.connect("clicked", self.app.on_refresh_status_clicked)
        action_row.pack_start(self.refresh_button, True, True, 0)

        # Footer row sits below the main control card
        footer_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_start(footer_row, False, False, 0)

        # Footer text stays on the left
        self.info_label = self.make_label("Manufactured by Mushy", xalign=0)
        self.info_label.set_line_wrap(True)
        self.info_label.set_max_width_chars(20)
        self.info_label.get_style_context().add_class("hero-caption")
        footer_row.pack_start(self.info_label, True, True, 0)

        # Open the separate account page from the footer
        self.sign_out_button = Gtk.Button()
        self.sign_out_button.get_style_context().add_class("signout-button")
        self.sign_out_button.connect("clicked", self.app.on_open_account_page_clicked)
        self.sign_out_button.set_tooltip_text("Open the account page.")
        account_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.sign_out_button.add(account_button_box)

        account_label = Gtk.Label(label="Account")
        account_button_box.pack_start(account_label, False, False, 0)

        self.account_indicator_label = Gtk.Label()
        account_button_box.pack_start(self.account_indicator_label, False, False, 0)
        self.set_account_indicator("unknown")
        footer_row.pack_end(self.sign_out_button, False, False, 0)

    def make_label(self, text="", xalign=0, wrap=False):
        # Small helper so labels are created the same way each time
        label = Gtk.Label(label=text)
        label.set_xalign(xalign)
        label.set_line_wrap(wrap)
        return label

    def make_markup_label(self, markup="", xalign=0, wrap=False):
        # Helper for labels that use colored markup
        label = Gtk.Label()
        label.set_markup(markup)
        label.set_xalign(xalign)
        label.set_line_wrap(wrap)
        return label

    def set_toggle_button_icon(self, icon_path):
        # Show a custom image on the main on/off button
        icon_path = os.fspath(icon_path)
        if not os.path.exists(icon_path):
            self.toggle_button.set_label("Toggle")
            self.toggle_button.set_image(None)
            return

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            icon_path,
            width=170,
            height=136,
            preserve_aspect_ratio=True
        )
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        self.toggle_button.set_always_show_image(True)
        self.toggle_button.set_image(image)
        self.toggle_button.set_label("")

    def set_home_message(self, text):
        # Footer copy doubles as lightweight status and error feedback
        self.info_label.set_text(text)

    def set_subtitle_text(self, text):
        self.subtitle_label.set_text(text)

    def set_account_indicator(self, state):
        if state == "signed_in":
            self.account_indicator_label.set_markup('<span foreground="#1DB954">✓</span>')
            self.sign_out_button.set_tooltip_text("Account page: signed in.")
            return

        if state == "signed_out":
            self.account_indicator_label.set_markup('<span foreground="#D64541">✗</span>')
            self.sign_out_button.set_tooltip_text("Account page: not signed in.")
            return

        self.account_indicator_label.set_markup('<span foreground="#97a9bc">?</span>')
        self.sign_out_button.set_tooltip_text("Open the account page.")
