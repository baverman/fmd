import gtk
import gio

import pyexo
pyexo.require('0.6')
import exo

class FileList(object):
    def __init__(self):
        self.model = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        self.emodel = gtk.ListStore(gtk.gdk.Pixbuf, str, str)

        self.widget = gtk.VBox()

        self.uri_entry = gtk.Entry()
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

    def set_uri(self, uri):
        self.uri_entry.set_text(uri)
        self.view.grab_focus()
        self.fill(uri)

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

    def fill(self, uri):
        self.view.set_model(self.emodel)

        folder = gio.file_parse_name(uri)
        enumerator = folder.enumerate_children('standard::*')

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

        for _, _, name, info in sorted(infos):
            self.model.append((self.get_pixbuf(info), name, None))

        self.view.set_model(self.model)
