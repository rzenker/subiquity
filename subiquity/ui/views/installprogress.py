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

import logging
from urwid import (
    LineBox,
    Text,
    SimpleFocusListWalker,
    )

from subiquitycore.view import BaseView
from subiquitycore.ui.buttons import cancel_btn, ok_btn, reset_btn
from subiquitycore.ui.container import ListBox, Pile
from subiquitycore.ui.utils import button_pile, Padding

log = logging.getLogger("subiquity.views.installprogress")

class MyLineBox(LineBox):
    def format_title(self, title):
        if title:
            return [" ", title, " "]
        else:
            return ""


class ProgressView(BaseView):
    def __init__(self, model, controller):
        self.model = model
        self.controller = controller

        self.log_listwalker = SimpleFocusListWalker([])
        self.close_log_btn = reset_btn(label="Close", on_press=self.close_log)
        self.log_pile = MyLineBox(Pile([
            ('weight', 1, ListBox(self.log_listwalker)),
            ('pack', Text("")),
            ('pack', button_pile([self.close_log_btn])),
            ]), "Raw Curtin Logs")

        self.event_listwalker = SimpleFocusListWalker([])
        self.eventbox = MyLineBox(ListBox(self.event_listwalker))
        self.reboot_btn = ok_btn(label=_("Reboot Now"), on_press=self.reboot)
        self.exit_btn = cancel_btn(label=_("Exit To Shell"), on_press=self.quit)
        self.show_log_btn = reset_btn(label=_("Show full log"), on_press=self.show_logs)
        self.event_buttons = button_pile([self.reboot_btn, self.exit_btn, self.show_log_btn])
        del self.event_buttons.base_widget.contents[:2]
        body = [
            ('pack', Text("")),
            ('weight', 1, Padding.center_79(self.eventbox)),
            ('pack', Text("")),
            ('pack', self.event_buttons),
            ('pack', Text("")),
        ]
        self.event_pile = Pile(body)
        super().__init__(self.event_pile)

    def add_log_tail(self, text):
        for line in text.splitlines():
            self.log_listwalker.append(Text(line))
        self.log_listwalker.set_focus(len(self.log_listwalker) - 1)

    def clear_log_tail(self):
        self.log_listwalker[:] = []
        self.event_listwalker[:] = []

    def new_stage(self, stage):
        self.event_listwalker.append(Text(stage))

    def set_status(self, text):
        self.eventbox.set_title(text)

    def show_complete(self, include_exit=False):
        c = self.event_buttons.base_widget.contents
        c[0:0] = [self.reboot_btn]
        if include_exit:
            c[1:1] = [self.exit_btn]
        self.event_pile.focus_position = 3
        self.event_buttons.base_widget.focus_position = 0

    def reboot(self, btn):
        self.controller.reboot()

    def quit(self, btn):
        self.controller.quit()

    def show_logs(self, btn):
        self._w = self.log_pile

    def close_log(self, btn):
        self._w = self.event_pile
