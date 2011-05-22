import gtk
import gio

import pyexo
pyexo.require('0.6')
import exo

def init(activator):
    activator.bind_accel('navigate/parent', 'Navigate to parent directory',
        '<alt>Up', FileList.navigate_parent)

    activator.bind_accel('navigate/back', 'Navigate back in history',
        '<alt>Left', FileList.navigate_back)
    activator.map('navigate/back', 'BackSpace')

    activator.bind_accel('navigate/forward', 'Navigate forward in history',
        '<alt>Right', FileList.navigate_forward)


class History(object):
    def __init__(self):
        self.places = {}
        self.hline = []
        self.current = 0

    def add(self, path):
        self.hline = self.hline[:self.current] + [path]
        self.current += 1

    def update(self, path, cursor, scroll):
        self.places[path] = (cursor, scroll)

    def get(self, path):
        return self.placec.get(path, (None, None))

    def back(self):
        if self.current > 0:
            self.current -= 1
            path = self.hline[self.current]
            return (path,) + self.get(path)
        else:
            return None, None, None

    def forward(self):
        if self.current < len(self.hline):
            path = self.hline[self.current]
            self.current += 1
            return (path,) + self.get(path)
        else:
            return None, None, None


class FileList(object):
    def __init__(self):
        self.model = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        self.emodel = gtk.ListStore(gtk.gdk.Pixbuf, str, str)

        self.widget = gtk.VBox()

        self.uri_entry = gtk.Entry()
        self.uri_entry.connect('activate', self.on_uri_entry_activate)
        self.widget.pack_start(self.uri_entry, False, False)

        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_NEVER)

        self.widget.pack_start(self.sw)

        self.view = view = exo.IconView()
        view.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        view.props.layout_mode = 1
        view.set_selection_mode(gtk.SELECTION_MULTIPLE)
        view.set_margin(3)
        view.set_row_spacing(0)
        view.set_spacing(0)
        view.set_single_click(True)
        view.set_single_click_timeout(1000)
        view.connect('item-activated', self.on_item_activated)

        icon_cell = gtk.CellRendererPixbuf()
        view.pack_start(icon_cell, False)
        view.set_attributes(icon_cell, pixbuf=0)
        icon_cell.props.follow_state = True
        icon_cell.props.xpad = 1

        text_cell = exo.CellRendererEllipsizedText()
        view.pack_start(text_cell, True)
        view.set_attributes(text_cell, text=1)
        text_cell.props.follow_state = True

        self.sw.add(view)

        self.icon_cache = {}
        self.current_folder = None
        self.history = History()

    def set_uri(self, uri, cursor=None, scroll=None):
        self.uri_entry.set_text(uri)
        self.update(uri, cursor, scroll)

    def update(self, uri, cursor=None, scroll=None):
        self.view.grab_focus()
        self.fill(uri, cursor=None, scroll=None)

    def get_pixbuf(self, info):
        content_type = info.get_attribute_as_string('standard::content-type')
        try:
            return self.icon_cache[content_type]
        except KeyError:
            pass

        theme = gtk.icon_theme_get_default()
        icon_info = theme.lookup_by_gicon(gio.content_type_get_icon(content_type), 16, 0)

        if not icon_info:
            icon_info = theme.lookup_icon('gtk-file', 16, 0)

        if icon_info:
            pixbuf = icon_info.load_icon()
        else:
            pixbuf = None

        self.icon_cache[content_type] = pixbuf
        return pixbuf

    def fill(self, uri, cursor=None, scroll=None):
        self.view.set_model(self.emodel)

        if self.current_folder:
            self.history.update(self.current_folder.get_path(), None,
                self.sw.props.hadjustment.value)

            print self.view.get_cursor()


        self.current_folder = gio.file_parse_name(uri)
        enumerator = self.current_folder.enumerate_children('standard::*')

        infos = []
        while True:
            fi = enumerator.next_file()
            if not fi:
                break

            if fi.get_attribute_boolean('standard::is-hidden'):
                continue

            content_type = fi.get_attribute_as_string('standard::content-type')
            sk = 0 if content_type == 'inode/directory' else 1
            name = fi.get_attribute_as_string('standard::display-name')
            infos.append((sk, name.lower(), name, fi))

        enumerator.close()

        self.model.clear()
        for _, _, name, info in sorted(infos):
            self.model.append((self.get_pixbuf(info), name, None))

        self.sw.props.hadjustment.value = 0
        self.view.set_model(self.model)

    def on_uri_entry_activate(self, entry):
        self.update(entry.get_text())

    def on_item_activated(self, view, path):
        row = self.model[path]
        self.set_uri(self.current_folder.get_child_for_display_name(row[1]).get_path())

    def navigate_parent(self):
        parent = self.current_folder.get_parent()
        if parent:
            self.set_uri(parent.get_path())

    def navigate_back(self):
        print 'back'

    def navigate_forward(self):
        print 'forward'