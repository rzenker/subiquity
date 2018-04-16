# Portions Copyright 2017 Canonical, Ltd.
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

# This is adapted from
# https://github.com/pimutils/khal/commit/bd7c5f928a7670de9afae5657e66c6dc846688ac, which has this license:
#
# Copyright (c) 2013-2015 Christian Geier et al.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Extended versions of urwid containers.

This module provides versions of urwid's Columns, Pile and ListBox
containers. It adds support for tab-cycling, callbacks on
gaining/losing focus and scrollbars on listboxes.

 1. Tab-cycling

Tab advances to the next selectable item and wraps when it gets to the
end of the screen. Shift tab goes the other way. In addition, an
unhandled "enter" key also advances to the next selectable item.

 2. Callbacks when a widget gains/loses focus

Define lost_focus or gained_focus callbacks on widgets and they'll be
called when the widget gains or loses focus.

 3. Scrollbars on ListBoxes.

All ListBoxes in subiquity gain a scrollbar when their contents don't
entirely fit on screen. The implementation assumes that there are not
too many elements in the ListBox.
"""

import logging

import urwid

log = logging.getLogger('subiquitycore.ui.container')

# The theory of tab-cycling:
#
# Tab should advance to the next selectable item and wrap when it gets
# to the end of the screen. Sounds simple, right? Well...
#
# Moving to the next selectable item within a container is pretty
# simple (it's what up and down do, after all). When a container is
# tabbed into, the first selectable within that container is selected
# and vv when it's shift tabbed into, the last selectable is
# selected. Urwid doesn't provide a native way to do that but it's
# pretty simple to implement (see the _select_first_selectable /
# _select_last_selectable methods). The tricky part is wrapping
# around: only the "outermost" container should wrap around. Urwid
# doesn't provide much of a way for a container to know about what it
# is contained in, so what this code does is, when interpreting a key
# that maps to either of the next selectable / prev selectable
# commands, passes a different key (the same key with " no wrap"
# appended) down to its contained widget. Then any containers within
# the outer one know not to wrap around in response to such a key.
#
# There is no support for a tab cycling Columns. It wouldn't be any
# harder than Pile but as subiquity is intended to be navigable with
# only up, down and enter, it doesn't actually contain any Columns
# with more than one selectable (this constraint is enforced by the
# Columns in this module).


def _maybe_call(w, methname):
    if w is None:
        return
    m = getattr(w.base_widget, methname, None)
    if m is not None:
        m()


def _has_other_selectable(widgets, cur_focus):
    for i, w in enumerate(widgets):
        if i != cur_focus and w.selectable():
            return True
    return False



for key, command in list(urwid.command_map._command.items()):
    if command in ('next selectable', 'prev selectable', urwid.ACTIVATE):
        urwid.command_map[key + ' no wrap'] = command

enter_advancing_command_map = urwid.command_map.copy()
enter_advancing_command_map['enter'] = 'next selectable'
enter_advancing_command_map['enter no wrap'] = 'next selectable'


class TabCyclingPile(urwid.Pile):
    _command_map = enter_advancing_command_map

    def selectable(self):
        for w, _ in self.contents:
            if w.selectable():
                return True
        return False

    def _select_first_selectable(self):
        """Select first selectable child (possibily recursively)."""
        for i, (w, o) in enumerate(self.contents):
            if w.selectable():
                self.set_focus(i)
                _maybe_call(w, "_select_first_selectable")
                return

    def _select_last_selectable(self):
        """Select last selectable child (possibily recursively)."""
        for i, (w, o) in reversed(list(enumerate(self.contents))):
            if w.selectable():
                self.set_focus(i)
                _maybe_call(w, "_select_last_selectable")
                return

    def _widgets(self):
        return [w for (w, o) in self._contents]

    # This is a copy/paste/hack of urwid's implementation. The main
    # reason we can't do this via simple subclassing is the need to
    # call _select_{first,last}_selectable on the newly focused
    # element when the focus changes.
    def keypress(self, size, key ):
        """Pass the keypress to the widget in focus.
        Unhandled 'up' and 'down' keys may cause a focus change."""
        if not self.contents:
            return key

        # start subiquity change: new code
        downkey = key
        if not key.endswith(' no wrap') and self._command_map[key] in ('next selectable', 'prev selectable'):
            if _has_other_selectable(self._widgets(), self.focus_position):
                downkey += ' no wrap'
        # end subiquity change

        item_rows = None
        if len(size) == 2:
            item_rows = self.get_item_rows(size, focus=True)

        i = self.focus_position
        if self.selectable():
            tsize = self.get_item_size(size, i, True, item_rows)
            # start subiquity change: pass downkey to focus, not key, do not return if command_map[upkey] is next/prev selectable
            upkey = self.focus.keypress(tsize, downkey)
            if self._command_map[upkey] not in ('cursor up', 'cursor down', 'next selectable', 'prev selectable'):
                return upkey
            # end subiquity change

        # begin subiquity change: new code
        if self._command_map[key] == 'next selectable':
            next_fp = self.focus_position + 1
            for i, (w, o) in enumerate(self._contents[next_fp:], next_fp):
                if w.selectable():
                    self.set_focus(i)
                    _maybe_call(w, "_select_first_selectable")
                    return
            if not key.endswith(' no wrap'):
                self._select_first_selectable()
            return key
        elif self._command_map[key] == 'prev selectable':
            for i, (w, o) in reversed(list(enumerate(self._contents[:self.focus_position]))):
                if w.selectable():
                    self.set_focus(i)
                    _maybe_call(w, "_select_last_selectable")
                    return
            if not key.endswith(' no wrap'):
                self._select_last_selectable()
            return key
        # continued subiquity change: set 'meth' appropriately
        elif self._command_map[key] == 'cursor up':
            candidates = list(range(i-1, -1, -1)) # count backwards to 0
            meth = '_select_last_selectable'
        else: # self._command_map[key] == 'cursor down'
            candidates = list(range(i+1, len(self.contents)))
            meth = '_select_first_selectable'
        # end subiquity change

        if not item_rows:
            item_rows = self.get_item_rows(size, focus=True)

        for j in candidates:
            if not self.contents[j][0].selectable():
                continue

            self._update_pref_col_from_focus(size)
            self.focus_position = j
            # begin subiquity change: new code
            _maybe_call(self.focus, meth)
            # end subiquity change
            if not hasattr(self.focus, 'move_cursor_to_coords'):
                return

            rows = item_rows[j]
            if self._command_map[key] == 'cursor up':
                rowlist = list(range(rows-1, -1, -1))
            else: # self._command_map[key] == 'cursor down'
                rowlist = list(range(rows))
            for row in rowlist:
                tsize = self.get_item_size(size, j, True, item_rows)
                if self.focus_item.move_cursor_to_coords(
                        tsize, self.pref_col, row):
                    break
            return

        # nothing to select
        return key


class OneSelectableColumns(urwid.Columns):
    def __init__(self, widget_list, dividechars=0, focus_column=None,
        min_width=1, box_columns=None):
        super().__init__(widget_list, dividechars, focus_column, min_width, box_columns)
        selectables = 0
        for w, o in self._contents:
            if w.selectable():
                selectables +=1
        if selectables > 1:
            raise Exception("subiquity only supports one selectable in a Columns")



class TabCyclingListBox(urwid.ListBox):
    _command_map = enter_advancing_command_map

    def __init__(self, body):
        # urwid.ListBox converts an arbitrary sequence argument to a
        # PollingListWalker, which doesn't work with the below code.
        if getattr(body, 'get_focus', None) is None:
            body = urwid.SimpleFocusListWalker(body)
        super().__init__(body)

    def _set_focus_no_move(self, i):
        # We call set_focus twice because otherwise the listbox
        # attempts to do the minimal amount of scrolling required to
        # get the new focus widget into view, which is not what we
        # want, as if our first widget is a compound widget it results
        # its last widget being focused -- in fact the opposite of
        # what we want!
        self.set_focus(i)
        self.set_focus(i)
        # I don't really understand why this is required but it seems it is.
        self._invalidate()

    def _select_first_selectable(self):
        """Select first selectable child (possibily recursively)."""
        for i, w in enumerate(self.body):
            if w.selectable():
                self._set_focus_no_move(i)
                _maybe_call(w, "_select_first_selectable")
                return

    def _select_last_selectable(self):
        """Select last selectable child (possibily recursively)."""
        for i, w in reversed(list(enumerate(self.body))):
            if w.selectable():
                self._set_focus_no_move(i)
                _maybe_call(w, "_select_last_selectable")
                return

    def keypress(self, size, key):
        downkey = key
        if not key.endswith(' no wrap') and self._command_map[key] in ('next selectable', 'prev selectable'):
            if _has_other_selectable(self.body, self.focus_position):
                downkey += ' no wrap'
        upkey = super().keypress(size, downkey)
        if upkey != downkey:
            key = upkey

        if len(self.body) == 0:
            return key

        if self._command_map[key] == 'next selectable':
            next_fp = self.focus_position + 1
            for i, w in enumerate(self.body[next_fp:], next_fp):
                if w.selectable():
                    self.set_focus(i)
                    _maybe_call(w, "_select_first_selectable")
                    return None
            if not key.endswith(' no wrap'):
                self._select_first_selectable()
            return key
        elif self._command_map[key] == 'prev selectable':
            for i, w in reversed(list(enumerate(self.body[:self.focus_position]))):
                if w.selectable():
                    self.set_focus(i)
                    _maybe_call(w, "_select_last_selectable")
                    return None
            if not key.endswith(' no wrap'):
                self._select_last_selectable()
            return key
        else:
            return key


class FocusTrackingMixin:

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._contents.set_focus_changed_callback(self._focus_changed)

    def lost_focus(self):
        try:
            cur_focus = self.focus
        except IndexError:
            pass
        else:
            _maybe_call(cur_focus, 'lost_focus')

    def gained_focus(self):
        _maybe_call(self.focus, 'gained_focus')

    def _focus_changed(self, new_focus):
        try:
            cur_focus = self.focus
        except IndexError:
            pass
        else:
            _maybe_call(cur_focus, 'lost_focus')
        _maybe_call(self[new_focus], 'gained_focus')
        self._invalidate()


class FocusTrackingPile(FocusTrackingMixin, TabCyclingPile):
    pass

class FocusTrackingColumns(FocusTrackingMixin, OneSelectableColumns):
    pass


class FocusTrackingListBox(TabCyclingListBox):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.body.set_focus_changed_callback(self._focus_changed)
        self._in_set_focus_complete = False

    def _focus_changed(self, new_focus):
        if not self._in_set_focus_complete:
            _maybe_call(self.focus, 'lost_focus')
            _maybe_call(self.body[new_focus], 'gained_focus')
            self._invalidate()

    def lost_focus(self):
        _maybe_call(self.focus, 'lost_focus')

    def gained_focus(self):
        _maybe_call(self.focus, 'gained_focus')

    def _set_focus_complete(self, size, focus):
        self._in_set_focus_complete = True
        try:
            super()._set_focus_complete(size, focus)
        finally:
            self._in_set_focus_complete = False


Columns = FocusTrackingColumns
Pile = FocusTrackingPile


class ScrollBarListBox(FocusTrackingListBox):

    def __init__(self, walker=None):
        def f(char, attr):
            return urwid.AttrMap(urwid.SolidFill(char), attr)
        self.bar = Pile([
            ('weight', 1, f("\N{BOX DRAWINGS LIGHT VERTICAL}", 'scrollbar_bg')),
            ('weight', 1, urwid.AttrMap(urwid.SolidFill("\N{FULL BLOCK}"), 'scrollbar_fg', 'danger_button focus')),
            ('weight', 1, f("\N{BOX DRAWINGS LIGHT VERTICAL}", 'scrollbar_bg')),
            ])
        super().__init__(walker)

    def render(self, size, focus=False):
        visible = self.ends_visible(size, focus)
        if len(visible) == 2:
            return super().render(size, focus)
        else:
            # This implementation assumes that the number of rows is
            # not too large (and in particular is finite). That's the
            # case for all the listboxes we have in subiquity today.
            maxcol, maxrow = size

            offset, inset = self.get_focus_offset_inset((maxcol - 1, maxrow))

            seen_focus = False
            height = height_before_focus = 0
            focus_widget, focus_pos = self.body.get_focus()
            # Scan through the rows calculating total height and the
            # height of the rows before the focus widget.
            for widget in self.body:
                rows = widget.rows((maxcol - 1,))
                if widget is focus_widget:
                    seen_focus = True
                elif not seen_focus:
                    height_before_focus += rows
                height += rows

            # Calculate the number of rows off the top and bottom of
            # the listbox.
            if 'top' in visible:
                top = 0
            else:
                top = height_before_focus + inset - offset
            if 'bottom' in visible:
                bottom = 0
            else:
                bottom = height - top - maxrow

            # Prevent the box from being squished to 0 rows. Input of
            #
            #     ('weight', maxrow)
            #
            # gets
            #
            #     round(maxrow / (top + maxrow + bottom))
            #
            # rows and that being < 1 simplifies to the below).
            if maxrow*maxrow < height:
                boxopt = self.bar.options('given', 1)
            else:
                boxopt = self.bar.options('weight', maxrow)

            self.bar.contents[:] = [
                (self.bar.contents[0][0], self.bar.options('weight', top)),
                (self.bar.contents[1][0], boxopt),
                (self.bar.contents[2][0], self.bar.options('weight', bottom)),
                ]
            canvases = [
                (super().render((maxcol - 1, maxrow), focus), self.focus_position, True, maxcol - 1),
                (self.bar.render((1, maxrow), focus), None, False, 1)
                ]
            return urwid.CanvasJoin(canvases)


ListBox = ScrollBarListBox

class MyOverlay(urwid.Widget):
    _selectable = True
    _sizing = frozenset([urwid.BOX])
    def __init__(self, bottom_w):
        self.bottom_w = bottom_w
        self.top_w = None
        self.top_stretchy_index = None

    def show_my_overlay(self, title, widgets, stretchy_index, focus_index):
        self.top_stretchy_index = stretchy_index
        def entry(i, w):
            if i == stretchy_index:
                return ('weight', 1, ListBox([w]))
            else:
                return ('pack', w)
        self.top_w = urwid.Filler(
            urwid.Padding(
                urwid.LineBox(
                    urwid.Filler(
                        urwid.Padding(
                            Pile(
                                [entry(i, w) for (i, w) in enumerate(widgets)],
                                focus_item=widgets[focus_index]),
                            left=2, right=2),
                        top=1, bottom=1, height=('relative', 100)),
                    title=title),
                left=3, right=3),
            top=1, bottom=1, height=('relative', 100))
        self._invalidate()

    def remove_my_overlay(self):
        self.top_w = None
        self._invalidate()

    def _top_size(self, size, focus):
        maxcol, maxrow = size # we are a BOX widget
        maxcol = min(maxcol, 72)
        fixed_rows = 6 # lines at top and bottom and padding
        available_stretchy_rows = maxrow - fixed_rows
        for i, (widget, opt) in enumerate(self.top_w.base_widget.contents):
            if i == self.top_stretchy_index:
                stretchy_w = widget.contents()[0][0]
            elif urwid.FLOW in widget.sizing():
                rows = widget.rows((maxcol-8,), focus)
                available_stretchy_rows -= rows
                fixed_rows += rows
            else:
                w_size = widget.pack((), focus)
                available_stretchy_rows -= w_size[1]
                fixed_rows += w_size[1]
        if available_stretchy_rows < 1:
            1/0
        stretchy_ideal_rows = stretchy_w.rows((maxcol-8,), focus)
        scrollbar = stretchy_ideal_rows > available_stretchy_rows
        if available_stretchy_rows > stretchy_ideal_rows:
            return (maxcol, stretchy_ideal_rows + fixed_rows), scrollbar
        else:
            return (maxcol, size[1]), scrollbar

    def keypress(self, size, key):
        if self.top_w is None:
            return self.bottom_w.keypress(size, key)
        else:
            top_size, scrollbar = self._top_size(size, True)
            lb = self.top_w.base_widget.contents[self.top_stretchy_index][0]
            lb._selectable = scrollbar
            return self.top_w.keypress(top_size, key)

    def render(self, size, focus):
        bottom_c = self.bottom_w.render(size, focus and self.top_w is None)
        if self.top_w is None or not bottom_c.cols() or not bottom_c.rows():
            return urwid.CompositeCanvas(bottom_c)

        top_size, scrollbar = self._top_size(size, focus)
        top_c = self.top_w.render(top_size, focus)
        top_c = urwid.CompositeCanvas(top_c)
        top = (size[1] - top_size[1]) // 2
        left = (size[0] - top_size[0]) // 2
        return urwid.CanvasOverlay(top_c, bottom_c, left, top)
