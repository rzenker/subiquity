# Copyright 2015 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Install Path

Provides high level options for Ubuntu install

"""
import logging
import re
from urwid import connect_signal, Text

from subiquitycore.ui.buttons import back_btn, forward_btn
from subiquitycore.ui.utils import Padding, button_pile
from subiquitycore.ui.container import ListBox, Pile
from subiquitycore.view import BaseView
from subiquity.ui.views.identity import UsernameField, PasswordField, USERNAME_MAXLEN
from subiquitycore.ui.form import (
    Form,
    URLField,
)


log = logging.getLogger('subiquity.installpath')


class InstallpathView(BaseView):
    def __init__(self, model, controller):
        self.model = model
        self.controller = controller
        self.items = []
        back = back_btn(_("Back"), on_press=self.cancel)
        self.body = [
            ('pack', Text("")),
            Padding.center_79(self._build_choices()),
            ('pack', Text("")),
            ('pack', button_pile([back])),
            ('pack', Text("")),
        ]
        super().__init__(Pile(self.body))

    def _build_choices(self):
        choices = []
        for label, path in self.model.paths:
            log.debug("Building inputs: {}".format(path))
            choices.append(
                forward_btn(
                    label=label, on_press=self.confirm, user_arg=path))
        return ListBox(choices)

    def confirm(self, sender, path):
        self.controller.choose_path(path)

    def cancel(self, button=None):
        self.controller.cancel()

class RegionForm(Form):

    username = UsernameField(
        _("Pick a username for the admin account:"),
        help=_("Enter the administrative username."))
    password = PasswordField(
        _("Choose a password:"),
        help=_("Please enter the password for this account."))

    def validate_username(self):
        if len(self.username.value) < 1:
            return _("Username missing")

        if len(self.username.value) > USERNAME_MAXLEN:
            return _("Username too long, must be < ") + str(USERNAME_MAXLEN)

        if not re.match(r'[a-z_][a-z0-9_-]*', self.username.value):
            return _("Username must match NAME_REGEX, i.e. [a-z_][a-z0-9_-]*")

    def validate_password(self):
        if len(self.password.value) < 1:
            return _("Password must be set")


class RackForm(Form):

    url = URLField(
        _("Ubuntu MAAS Region API address:"),
        help=_(
            "e.g. \"http://192.168.1.1:5240/MAAS\". "
            "localhost or 127.0.0.1 are not useful values here." ))

    secret = PasswordField(
        _("MAAS shared secret:"),
        help=_(
            "The secret can be found in /var/lib/maas/secret "
            "on the region controller. " ))

    def validate_url(self):
        if len(self.url.value) < 1:
            return _("API address must be set")

    def validate_secret(self):
        if len(self.secret.value) < 1:
            return _("Secret must be set")


class MAASView(BaseView):

    def __init__(self, model, controller):
        self.model = model
        self.controller = controller
        self.signal = controller.signal
        self.items = []

        if self.model.path == "maas_region":
            self.form = RegionForm()
        elif self.model.path == "maas_rack":
            self.form = RackForm()
        else:
            raise ValueError("invalid MAAS form %s" % self.model.path)

        connect_signal(self.form, 'submit', self.done)
        connect_signal(self.form, 'cancel', self.cancel)

        super().__init__(self.form.as_screen(self, focus_buttons=False))

    def done(self, result):
        log.debug("User input: {}".format(result.as_data()))
        self.controller.setup_maas(result.as_data())

    def cancel(self, result=None):
        self.controller.default()
