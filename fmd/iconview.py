import bisect
import gtk
import gobject

from gtk.gdk import Rectangle
from gtk import keysyms

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


class FmdIconView(gtk.DrawingArea):
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
        gtk.DrawingArea.__init__(self)

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
        self.selected = {}
        self.cursor = None

        self.item_draw_queue = []

    def set_attributes(self, cell, **kwargs):
        self.cell_attrs[cell] = kwargs

    def _prepare_cell(self, cell, row):
        for k, v in self.cell_attrs.get(cell, {}).items():
            cell.set_property(k, row[v])

    def set_cursor(self, path, select=True):
        prev = self.cursor
        self.cursor = path
        if select:
            self.selected.clear()
            self.selected[path] = True

        if self.model:
            if prev:
                self._queue_path_draw(prev)

            self._queue_path_draw(self.cursor)

    def get_cursor(self):
        return self.cursor

    def _draw_item(self, item, row, xoffset, earea):
        flags = 0
        if row.path in self.selected:
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

        if self.item_draw_queue:
            while self.item_draw_queue:
                path, item = self.item_draw_queue.pop(0)
                self._draw_item(item, self.model[path], xoffset, earea)
        else:
            idx = bisect.bisect(self.columns, xoffset + margin) - 1
            path = self.column_first_item[self.columns[idx]]
            while True:
                try:
                    r = self.model[path]
                    path = (path[0]+1,)
                except IndexError:
                    break

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
            maxx = self.update_item_cache()
            self._hadj.configure(0, 0, maxx, allocation.width*0.1, allocation.width*0.9,
                allocation.width)

    def do_set_scroll_adjustments(self, h_adjustment, v_adjustment):
        if h_adjustment:
            self._hscroll_handler_id = h_adjustment.connect(
                "value-changed", self.hscroll_value_changed)
            self._hadj = h_adjustment

    def hscroll_value_changed(self, *args):
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

        return x + mx

    def do_realize(self):
        gtk.DrawingArea.do_realize(self)
        self.window.set_background(self.style.base[gtk.STATE_NORMAL])

    def _queue_path_draw(self, path):
        item = self.item_cache[path]
        self.item_draw_queue.append((path, item))
        xoffset = int(self._hadj.value)
        self.window.invalidate_rect(Rectangle(item.x - xoffset, item.y,
            item.width, item.height), False)

    def do_key_press_event(self, event):
        if event.keyval == keysyms.Down:
            if not self.cursor:
                self.set_cursor((0,))
            elif self.cursor[0] + 1 < len(self.model):
                self.set_cursor((self.cursor[0] + 1,))

            return True

        if event.keyval == keysyms.Up:
            if self.cursor and self.cursor[0] > 0:
                self.set_cursor((self.cursor[0] - 1,))

            return True

        if event.keyval == keysyms.Return:
            if self.cursor:
                self.emit('item-activated', self.cursor)

            return True

        return False

gobject.type_register(FmdIconView)

gtk.widget_class_install_style_property(FmdIconView, ('hspacing', gobject.TYPE_INT,
    'Horizontal spacing', 'Horizontal spacing beetwen items', gobject.G_MININT, gobject.G_MAXINT,
    10, gobject.PARAM_READWRITE))

gtk.widget_class_install_style_property(FmdIconView, ('vspacing', gobject.TYPE_INT,
    'Vertical spacing', 'Vertical spacing beetwen items', gobject.G_MININT, gobject.G_MAXINT,
    2, gobject.PARAM_READWRITE))

gtk.widget_class_install_style_property(FmdIconView, ('margin', gobject.TYPE_INT,
    'Margin', 'Margin to view boundaries', gobject.G_MININT, gobject.G_MAXINT,
    3, gobject.PARAM_READWRITE))