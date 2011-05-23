import gtk
import gobject

from gtk.gdk import Rectangle


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
        "set-scroll-adjustments": (
            gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_ACTION,
            gobject.TYPE_NONE, (gtk.Adjustment, gtk.Adjustment)
        ),
    }

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.set_set_scroll_adjustments_signal("set-scroll-adjustments")
        self.model = None
        self.icon_renderer = None
        self.text_renderer = None
        self.cell_attrs = {}
        self.item_cache = {}
        self.margin = 3

    def set_attributes(self, cell, **kwargs):
        self.cell_attrs[cell] = kwargs

    def _prepare_cell(self, cell, row):
        for k, v in self.cell_attrs.get(cell, {}).items():
            cell.set_property(k, row[v])

    def do_expose_event(self, event):
        if not self.model:
            return True

        earea = event.area
        for r in self.model:
            item = self.item_cache[r.path]

            if item.x > earea:
                break

            self._prepare_cell(self.icon_renderer, r)
            area = Rectangle(item.x + item.ix, item.y + item.iy, item.iwidth, item.iheight)
            self.icon_renderer.render(self.window, self, area, area, earea, 0)

            self._prepare_cell(self.text_renderer, r)
            area = Rectangle(item.x + item.tx, item.y + item.ty, item.twidth, item.theight)
            self.text_renderer.render(self.window, self, area, area, earea, 0)

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
            print 'alloc', self.allocation

    def do_set_scroll_adjustments(self, h_adjustment, v_adjustment):
        if h_adjustment:
            self._hscroll_handler_id = h_adjustment.connect(
                "value-changed", self.hscroll_value_changed)
            self._hadj = h_adjustment

        if v_adjustment:
            self._vscroll_handler_id = v_adjustment.connect(
                "value-changed", self.vscroll_value_changed)
            self._vadj = v_adjustment

    def hscroll_value_changed(self, *args):
        print args

    def vscroll_value_changed(self, *args):
        print args

    def set_model(self, model):
        self.model = model
        self.update_item_cache()

    def update_item_cache(self):
        self.item_cache.clear()

        if not self.model:
            return

        x = y = self.margin
        maxy = self.allocation.height - self.margin
        mx = 0
        for r in self.model:
            self._prepare_cell(self.icon_renderer, r)
            self._prepare_cell(self.text_renderer, r)
            item = self.item_cache[r.path] = DrawItem(self, self.icon_renderer, self.text_renderer)

            ny = y + item.height
            if ny > maxy:
                x += mx
                mx = 0
                y = self.margin
                ny = y + item.height

            if item.width > mx:
                mx = item.width

            item.x = x
            item.y = y

            y = ny

    def do_realize(self):
        gtk.DrawingArea.do_realize(self)
        self.window.set_background(self.style.base[gtk.STATE_NORMAL])

gobject.type_register(FmdIconView)