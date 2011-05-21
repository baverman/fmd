import gtk
import gio

import pyexo
pyexo.require('0.6')
import exo

class FileList(object):
    def __init__(self):
        self.model = gtk.ListStore(str, str, str)
        self.emodel = gtk.ListStore(str, str, str)

        self.widget = gtk.VBox()

        self.uri_entry = gtk.Entry()
        self.widget.pack_start(self.uri_entry, False, False)

        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_NEVER)

        self.widget.pack_start(self.sw)

        self.view = view = exo.IconView()
        view.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        view.props.layout_mode = 1

        icon_cell = gtk.CellRendererPixbuf()
        view.pack_start(icon_cell, False)
        view.set_attributes(icon_cell, icon_name=0)

        text_cell = gtk.CellRendererText()
        view.pack_start(text_cell, True)
        view.set_attributes(text_cell, text=1)

        self.sw.add(view)

    def set_uri(self, uri):
        self.uri_entry.set_text(uri)
        self.view.grab_focus()
        self.fill(uri)

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
            infos.append((sk, name.lower(), name))

        enumerator.close()

        for _, _, name in sorted(infos):
            self.model.append((None, name, None))

        self.view.set_model(self.model)
