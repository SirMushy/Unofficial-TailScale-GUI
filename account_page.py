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
        self.set_size_request(360, 170)

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(header_row, False, False, 0)

        back_button = Gtk.Button(label="Back")
        back_button.connect("clicked", self.app.on_back_clicked)
        header_row.pack_start(back_button, False, False, 0)

        title_label = Gtk.Label()
        title_label.set_markup("<b>Account</b>")
        title_label.set_xalign(0)
        header_row.pack_start(title_label, False, False, 0)

        subtitle_label = Gtk.Label(
            label="Sign-in and sign-out controls will live here."
        )
        subtitle_label.set_xalign(0)
        subtitle_label.set_line_wrap(True)
        self.pack_start(subtitle_label, False, False, 0)

        self.status_label = Gtk.Label(label="Checking whether you are signed in...")
        self.status_label.set_xalign(0)
        self.status_label.set_line_wrap(True)
        self.pack_start(self.status_label, False, False, 0)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_row.set_homogeneous(True)
        self.pack_start(action_row, False, False, 0)

        self.sign_in_button = Gtk.Button(label="Sign In")
        self.sign_in_button.get_style_context().add_class("panel-button")
        action_row.pack_start(self.sign_in_button, True, True, 0)

        self.sign_out_button = Gtk.Button(label="Sign Out")
        self.sign_out_button.get_style_context().add_class("signout-button")
        action_row.pack_start(self.sign_out_button, True, True, 0)

    def set_account_status(self, text):
        self.status_label.set_text(text)
