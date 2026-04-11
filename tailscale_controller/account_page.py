# Load GTK for this page UI
import gi

# Tell Python we are using GTK 3
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


# Account page with placeholder sign-in/out actions
class AccountPage(Gtk.Box):

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.app = app
        self.set_border_width(10)
        self.set_size_request(360, 250)

        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        shell.get_style_context().add_class("account-shell")
        self.pack_start(shell, True, True, 0)

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_box.set_border_width(14)
        shell.pack_start(card_box, True, True, 0)

        header_overlay = Gtk.Overlay()
        card_box.pack_start(header_overlay, False, False, 0)

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_overlay.add(header_row)

        back_button = Gtk.Button(label="Back")
        back_button.get_style_context().add_class("panel-button")
        back_button.connect("clicked", self.app.on_back_clicked)
        header_row.pack_start(back_button, False, False, 0)

        title_block = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title_block.set_halign(Gtk.Align.CENTER)
        title_block.set_valign(Gtk.Align.CENTER)
        header_overlay.add_overlay(title_block)

        kicker_label = Gtk.Label()
        kicker_label.set_markup("<span size='small'><b>TAILNET ACCESS</b></span>")
        kicker_label.set_xalign(0.5)
        kicker_label.get_style_context().add_class("account-kicker")
        title_block.pack_start(kicker_label, False, False, 0)

        title_label = Gtk.Label()
        title_label.set_markup("<span size='x-large'><b>Account</b></span>")
        title_label.set_xalign(0.5)
        title_label.get_style_context().add_class("account-title")
        title_block.pack_start(title_label, False, False, 0)

        subtitle_label = Gtk.Label(
            label="Manage whether this device is signed in to your tailnet."
        )
        subtitle_label.set_xalign(0.5)
        subtitle_label.set_justify(Gtk.Justification.CENTER)
        subtitle_label.set_line_wrap(True)
        subtitle_label.get_style_context().add_class("account-subtitle")
        card_box.pack_start(subtitle_label, False, False, 0)

        status_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_frame.get_style_context().add_class("account-status-card")
        status_frame.set_border_width(12)
        card_box.pack_start(status_frame, False, False, 0)

        status_caption = Gtk.Label()
        status_caption.set_markup("<b>Current Account Status</b>")
        status_caption.set_xalign(0)
        status_caption.get_style_context().add_class("account-status-caption")
        status_frame.pack_start(status_caption, False, False, 0)

        status_top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_frame.pack_start(status_top_row, False, False, 0)

        self.state_pill_label = Gtk.Label()
        self.state_pill_label.set_xalign(0)
        self.state_pill_label.get_style_context().add_class("account-state-pill")
        status_top_row.pack_start(self.state_pill_label, False, False, 0)

        self.status_label = Gtk.Label(label="Checking whether you are signed in...")
        self.status_label.set_xalign(0)
        self.status_label.set_line_wrap(True)
        self.status_label.get_style_context().add_class("account-status-text")
        status_frame.pack_start(self.status_label, False, False, 0)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_row.set_homogeneous(True)
        card_box.pack_start(action_row, False, False, 0)

        self.sign_in_button = Gtk.Button(label="Sign In")
        self.sign_in_button.get_style_context().add_class("panel-button")
        self.sign_in_button.set_sensitive(False)
        self.sign_in_button.connect("clicked", self.app.on_sign_in_clicked)
        action_row.pack_start(self.sign_in_button, True, True, 0)

        self.sign_out_button = Gtk.Button(label="Sign Out")
        self.sign_out_button.get_style_context().add_class("signout-button")
        self.sign_out_button.set_sensitive(False)
        self.sign_out_button.connect("clicked", self.app.on_sign_out_clicked)
        action_row.pack_start(self.sign_out_button, True, True, 0)

        sudo_note_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sudo_note_box.get_style_context().add_class("account-note-box")
        sudo_note_box.set_border_width(10)
        card_box.pack_start(sudo_note_box, False, False, 0)

        left_warning_icon = Gtk.Label()
        left_warning_icon.set_markup("⚠")
        left_warning_icon.set_yalign(0)
        left_warning_icon.get_style_context().add_class("account-note-icon")
        sudo_note_box.pack_start(left_warning_icon, False, False, 0)

        sudo_note_label = Gtk.Label(
            label="Sign in and sign out will ask for sudo to run the commands."
        )
        sudo_note_label.set_xalign(0)
        sudo_note_label.set_line_wrap(True)
        sudo_note_label.get_style_context().add_class("account-note-text")
        sudo_note_box.pack_start(sudo_note_label, True, True, 0)

        right_warning_icon = Gtk.Label()
        right_warning_icon.set_markup("⚠")
        right_warning_icon.set_yalign(0)
        right_warning_icon.get_style_context().add_class("account-note-icon")
        sudo_note_box.pack_start(right_warning_icon, False, False, 0)

        self.set_account_state("unknown")

    def set_account_status(self, text):
        self.status_label.set_text(text)

    def set_action_buttons_enabled(self, signed_in_state, busy=False):
        if busy:
            self.sign_in_button.set_sensitive(False)
            self.sign_out_button.set_sensitive(False)
            self.sign_in_button.set_tooltip_text("Working...")
            self.sign_out_button.set_tooltip_text("Working...")
            return

        if signed_in_state == "signed_in":
            self.sign_in_button.set_sensitive(False)
            self.sign_out_button.set_sensitive(True)
            self.sign_in_button.set_tooltip_text("You are already signed in.")
            self.sign_out_button.set_tooltip_text("Sign out of Tailscale on this device.")
            return

        if signed_in_state == "signed_out":
            self.sign_in_button.set_sensitive(True)
            self.sign_out_button.set_sensitive(False)
            self.sign_in_button.set_tooltip_text("Sign in to Tailscale on this device.")
            self.sign_out_button.set_tooltip_text("You are already signed out.")
            return

        self.sign_in_button.set_sensitive(False)
        self.sign_out_button.set_sensitive(False)
        self.sign_in_button.set_tooltip_text("Checking account status...")
        self.sign_out_button.set_tooltip_text("Checking account status...")

    def set_account_state(self, state):
        style_context = self.state_pill_label.get_style_context()
        style_context.remove_class("account-state-pill-signed-in")
        style_context.remove_class("account-state-pill-signed-out")
        style_context.remove_class("account-state-pill-unknown")

        if state == "signed_in":
            label_text = "ONLINE"
            style_context.add_class("account-state-pill-signed-in")
        elif state == "signed_out":
            label_text = "OFFLINE"
            style_context.add_class("account-state-pill-signed-out")
        else:
            label_text = "CHECKING"
            style_context.add_class("account-state-pill-unknown")

        self.state_pill_label.set_text(label_text)
        self.set_action_buttons_enabled(state)
