import gtk
import gobject

from gtk.gdk import Rectangle


class DrawItem(object):
    def __init__(self, view, row):
        self.view = view
        self.iarea = Rectangle()
        self.tarea = Rectangle()
        self.width = 0
        self.height = 0

        self.refresh(row)

    def set_attrs(self, row):
        for k, v in self.view.icon_renderer_attrs.items():
            self.view.icon_renderer.set_property(k, row[v])

        for k, v in self.view.text_renderer_attrs.items():
            self.view.text_renderer.set_property(k, row[v])

    def refresh(self, row):
        self.set_attrs(row)
        c = self.iarea
        c.x, c.y, c.width, c.height = self.view.icon_renderer.get_size(self.view)

        c = self.tarea
        c.x, c.y, c.width, c.height = self.view.text_renderer.get_size(self.view)
        c.x += self.iarea.x + self.iarea.width

        u = self.iarea.union(self.tarea)
        self.height = u.height
        self.width = u.width

    def render(self, row, x, y, expose, flags):
        self.set_attrs(row)
        area = Rectangle(self.iarea.x + x, self.iarea.y + y, self.iarea.width, self.iarea.height)
        self.view.icon_renderer.render(self.view.window,
            self.view, area, area, expose, flags)

        area = Rectangle(self.tarea.x + x, self.tarea.y + y, self.tarea.width, self.tarea.height)
        self.view.text_renderer.render(self.view.window,
            self.view, area, area, expose, flags)

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
        self.icon_renderer_attrs = {}
        self.text_renderer = None
        self.text_renderer_attrs = {}
        self.item_cache = {}

    def set_icon_attributes(self, **kwargs):
        self.icon_renderer_attrs = kwargs

    def set_text_attributes(self, **kwargs):
        self.text_renderer_attrs = kwargs

    def do_expose_event(self, event):
        if not self.model:
            return True

        x = y = 0
        expose_area = event.area
        maxy = expose_area.y + expose_area.height
        maxx = expose_area.x + expose_area.width
        mx = 0
        for r in self.model:
            item = self.item_cache[r.path]

            ny = y + item.height
            if ny > maxy:
                x += mx
                mx = 0
                y = 0
                ny = y + item.height

            if x > maxx:
                break

            if item.width > mx:
                mx = item.width

            item.render(r, x, y, expose_area, 0)
            y = ny


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
            self.queue_draw()

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

        if self.model:
            for r in self.model:
                self.item_cache[r.path] = DrawItem(self, r)

    def do_realize(self):
        gtk.DrawingArea.do_realize(self)

gobject.type_register(FmdIconView)