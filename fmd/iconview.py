from bisect import bisect
import gtk
import gobject

from gtk.gdk import Rectangle, CONTROL_MASK, SHIFT_MASK
from gtk import keysyms

from uxie.utils import send_focus_change

class DrawItem(object):
    __slots__ = ['ix', 'iy', 'iwidth', 'iheight',
        'tx', 'ty', 'twidth', 'theight', 'width', 'height', 'x', 'y']

    def __init__(self, view, icell, tcell):
        self.ix, self.iy, self.iwidth, self.iheight = icell.get_size(view)
        self.tx, self.ty, self.twidth, self.theight = tcell.get_size(view)

        self.tx += self.ix + self.iwidth

        if self.theight > self.iheight:
            self.height = self.theight
            self.iy += (self.theight - self.iheight) / 2

        if self.theight < self.iheight:
            self.height = self.iheight
            self.ty += (self.iheight - self.theight) / 2

        self.width = self.tx + self.twidth


class FmdIconView(gtk.EventBox):
    __gsignals__ = {
        "expose-event": "override",
        "realize": "override",
        "size-request": "override",
        "size-allocate": "override",
        "key-press-event": "override",
        "set-scroll-adjustments": (
            gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_ACTION,
            gobject.TYPE_NONE, (gtk.Adjustment, gtk.Adjustment)
        ),
        "item-activated": (
            gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_ACTION,
            gobject.TYPE_NONE, (object,)
        ),
    }

    def __init__(self):
        gtk.EventBox.__init__(self)

        self.set_can_focus(True)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.KEY_PRESS_MASK)
        self.set_set_scroll_adjustments_signal("set-scroll-adjustments")

        self.model = None
        self.icon_renderer = None
        self.text_renderer = None
        self.cell_attrs = {}
        self.item_cache = {}
        self.columns = []
        self.column_first_item = {}
        self.cursor = None

        self.item_draw_queue = []
        self.needed_full_redraw = False

    def set_attributes(self, cell, **kwargs):
        self.cell_attrs[cell] = kwargs

    def _prepare_cell(self, cell, row):
        for k, v in self.cell_attrs.get(cell, {}).items():
            cell.set_property(k, row[v])

    def unselect_all(self):
        if self.model:
            for path in self.model.selection:
                self._queue_path_draw(path)

            self.model.clear_selection()

    def set_cursor(self, path, select=True, select_between=False):
        prev = self.cursor
        self.cursor = path

        if self.model:
            if select:
                self.unselect_all()
                self.model.select(path)

            if self.cursor not in self.item_cache:
                return

            if prev:
                self._queue_path_draw(prev)
                if select_between:
                    cursor = self.cursor
                    remove_selection = self.model.is_selected(cursor) and self.model.is_selected(prev)
                    if prev > self.cursor:
                         prev, cursor = cursor, prev

                    for path in self._foreach_path(prev, cursor):
                        if remove_selection and path != self.cursor:
                            self.model.unselect(path)
                        else:
                            self.model.select(path)

                        self._queue_path_draw(path)

            self._queue_path_draw(self.cursor)
            self.scroll_to_path(self.cursor)

    def get_cursor(self):
        return self.cursor

    def start_editing(self, path):
        event = gtk.gdk.Event(gtk.gdk.NOTHING)
        item = self.item_cache[path]
        xoffset = int(self._hadj.value)
        area = Rectangle(item.x + item.tx - xoffset, item.y + item.ty, item.twidth, item.theight)
        path = ','.join(map(str, path))

        entry = self.text_renderer.start_editing(event, self, path, area, area, 0)
        entry.start_editing(event)

        window = gtk.Window(gtk.WINDOW_POPUP)
        window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
        window.add(entry)
        entry.show()
        entry.realize()
        entry.size_allocate(area)

        win = self.window
        window.window.reparent(win, 0, 0)
        entry.size_allocate(area)
        window.resize(item.twidth, item.theight)
        window.move(item.x + item.tx - xoffset, item.y + item.ty)
        window.show()

        send_focus_change(entry, True)
        return entry

    def _draw_item(self, item, row, xoffset, earea):
        flags = 0
        if self.model.is_selected(row.path):
            flags = gtk.CELL_RENDERER_SELECTED
            self.style.paint_flat_box(self.window, gtk.STATE_SELECTED, gtk.SHADOW_NONE,
                earea, self, 'fmd icon text', item.x + item.tx - xoffset, item.y + item.ty,
                item.twidth, item.theight)

        self._prepare_cell(self.icon_renderer, row)
        area = Rectangle(item.x + item.ix - xoffset, item.y + item.iy, item.iwidth, item.iheight)
        self.icon_renderer.render(self.window, self, area, area, earea, flags)

        self._prepare_cell(self.text_renderer, row)
        area = Rectangle(item.x + item.tx - xoffset, item.y + item.ty, item.twidth, item.theight)
        self.text_renderer.render(self.window, self, area, area, earea, flags)

        if row.path == self.cursor:
            self.style.paint_focus(self.window, gtk.STATE_NORMAL,
                earea, self, 'fmd icon text focus', item.x + item.tx - xoffset, item.y + item.ty,
                item.twidth, item.theight)

    def do_expose_event(self, event):
        if not self.model:
            return True

        earea = event.area
        xoffset = int(self._hadj.value)
        margin = self.style_get_property('margin')

        if not self.needed_full_redraw and self.item_draw_queue:
            processed = {}
            while self.item_draw_queue:
                path, item = self.item_draw_queue.pop(0)
                if path in processed: continue
                self._draw_item(item, self.model[path], xoffset, earea)
                processed[path] = True
        else:
            self.item_draw_queue[:] = []
            self.needed_full_redraw = False
            idx = bisect(self.columns, xoffset + margin) - 1
            for path in self._foreach_path(self.column_first_item[self.columns[idx]]):
                r = self.model[path]
                item = self.item_cache[r.path]
                if item.x - xoffset > earea.width:
                    break

                self._draw_item(item, r, xoffset, earea)

        return True

    def do_size_request(self, req):
        if self.model:
            req.width = 500
            req.height = 500

    def do_size_allocate(self, allocation):
        self.allocation = allocation
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)
            self.update_item_cache()

    def do_set_scroll_adjustments(self, h_adjustment, v_adjustment):
        if h_adjustment:
            self._hscroll_handler_id = h_adjustment.connect(
                "value-changed", self.hscroll_value_changed)
            self._hadj = h_adjustment

    def hscroll_value_changed(self, *args):
        self.needed_full_redraw = True
        self.queue_draw()

    def set_model(self, model):
        self.model = model
        self.update_item_cache()

    def update_item_cache(self):
        self.item_cache.clear()
        self.columns[:] = []

        if not self.model:
            return

        hs = self.style_get_property('hspacing')
        vs = self.style_get_property('vspacing')
        margin = self.style_get_property('margin')

        x = y = margin
        maxy = self.allocation.height - margin
        mx = 0
        self.columns.append(x)
        self.column_first_item[x] = (0,)
        for r in self.model:
            self._prepare_cell(self.icon_renderer, r)
            self._prepare_cell(self.text_renderer, r)
            item = self.item_cache[r.path] = DrawItem(self, self.icon_renderer, self.text_renderer)

            ny = y + item.height + vs
            if ny > maxy:
                x += mx + hs
                self.columns.append(x)
                self.column_first_item[x] = r.path
                mx = 0
                y = margin
                ny = y + item.height + vs

            if item.width > mx:
                mx = item.width

            item.x = x
            item.y = y

            y = ny

        self._hadj.configure(0, 0, x+mx, self.allocation.width*0.1, self.allocation.width*0.9,
            self.allocation.width)

    def do_realize(self):
        gtk.DrawingArea.do_realize(self)
        self.window.set_background(self.style.base[gtk.STATE_NORMAL])

    def _queue_path_draw(self, path):
        try:
            item = self.item_cache[path]
        except KeyError:
            return

        self.item_draw_queue.append((path, item))
        xoffset = int(self._hadj.value)
        self.window.invalidate_rect(Rectangle(item.x - xoffset, item.y,
            item.width, item.height), False)

    def _foreach_path(self, fpath, tpath=None):
        tpath = tpath or (len(self.model)-1,)
        return ((r,) for r in xrange(fpath[0], tpath[0]+1))

    def _find_nearest_path_on_same_line(self, path, direction):
        item = self.item_cache[path]
        idx = bisect(self.columns, item.x) + direction - 1

        if idx < 0:
            return 0,
        elif idx >= len(self.columns):
            return len(self.model) - 1,

        path = self.column_first_item[self.columns[idx]]
        rpath = None
        dy = 0
        for path in self._foreach_path(path):
            it = self.item_cache[path]

            ndy = abs(it.y - item.y)
            if ndy == 0:
                return path

            if rpath and ndy > dy:
                return rpath

            rpath = path
            dy = ndy

        return path

    def scroll_to_path(self, path, align=None):
        item = self.item_cache[path]
        maxx = self.allocation.width
        xoffset = int(self._hadj.value)
        margin = self.style_get_property('margin')

        x1 = item.x - xoffset - margin
        x2 = x1 + item.width
        if align is None:
            if  0 <= x1 <= maxx and 0 <= x2 <= maxx:
                return
            elif x1 < 0:
                dx = x1
            elif x2 > maxx:
                dx = min(x1, x2 - maxx)
        else:
            dx = 0

        self._hadj.value = max(0, xoffset + dx)

    def do_key_press_event(self, event):
        keyval = event.keyval
        state = event.state

        if state | SHIFT_MASK | CONTROL_MASK == SHIFT_MASK | CONTROL_MASK:
            do_select_between = state == SHIFT_MASK
            do_select = not do_select_between and state != CONTROL_MASK

            if keyval == keysyms.Down:
                if not self.cursor:
                    self.set_cursor((0,))
                elif self.cursor[0] + 1 < len(self.model):
                    self.set_cursor((self.cursor[0] + 1,), do_select, do_select_between)

                return True

            if keyval == keysyms.Up:
                if self.cursor and self.cursor[0] > 0:
                    self.set_cursor((self.cursor[0] - 1,), do_select, do_select_between)

                return True

            if keyval == keysyms.Right:
                if not self.cursor:
                    self.set_cursor((0,))
                else:
                    cursor = self._find_nearest_path_on_same_line(self.cursor, 1)
                    if cursor:
                        self.set_cursor(cursor, do_select, do_select_between)

                return True

            if keyval == keysyms.Left:
                if self.cursor:
                    cursor = self._find_nearest_path_on_same_line(self.cursor, -1)
                    if cursor:
                        self.set_cursor(cursor, do_select, do_select_between)

                return True

        if keyval == keysyms.Return and not state:
            if self.cursor:
                self.emit('item-activated', self.cursor)

            return True

        if keyval == keysyms.space and state == CONTROL_MASK:
            if self.cursor:
                self.model.invert_selection(self.cursor)
                self._queue_path_draw(self.cursor)

            return True

        return False

    def refresh(self, full=True):
        if full:
            self.update_item_cache()

        self.needed_full_redraw = True
        self.queue_draw()


gobject.type_register(FmdIconView)

gtk.widget_class_install_style_property(FmdIconView, ('hspacing', gobject.TYPE_INT,
    'Horizontal spacing', 'Horizontal spacing between items', gobject.G_MININT, gobject.G_MAXINT,
    10, gobject.PARAM_READWRITE))

gtk.widget_class_install_style_property(FmdIconView, ('vspacing', gobject.TYPE_INT,
    'Vertical spacing', 'Vertical spacing between items', gobject.G_MININT, gobject.G_MAXINT,
    2, gobject.PARAM_READWRITE))

gtk.widget_class_install_style_property(FmdIconView, ('margin', gobject.TYPE_INT,
    'Margin', 'Margin to view boundaries', gobject.G_MININT, gobject.G_MAXINT,
    3, gobject.PARAM_READWRITE))