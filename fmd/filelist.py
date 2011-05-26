import os
import gtk
import gio

from uxie.search import InteractiveSearch

from .iconview import FmdIconView

def init(activator):
    activator.bind_accel('a_filelist', 'navigate/parent', 'Navigate to parent directory',
        '<alt>Up', FileList.navigate_parent)

    activator.bind_accel('a_filelist', 'navigate/back', 'Navigate back in history',
        '<alt>Left', FileList.navigate_back)
    activator.map('a_filelist', 'navigate/back', 'BackSpace')

    activator.bind_accel('a_filelist', 'navigate/forward', 'Navigate forward in history',
        '<alt>Right', FileList.navigate_forward)

    activator.bind_accel('filelist', 'view/hidden', 'Toggle hidden files',
        '<ctrl>h', FileList.show_hidden)

    activator.bind('s_filelist', 'copy', 'Copy', FileList.copy)
    activator.bind('s_filelist', 'cut', 'Cut', FileList.cut)
    activator.bind('filelist', 'paste', 'Paste', FileList.paste)
    activator.bind_accel('s_filelist', 'delete', 'Delete', 'Delete', FileList.delete)
    activator.bind_accel('s_filelist', 'force-delete', 'Force delete',
        '<shift>Delete', FileList.force_delete, 10)

    activator.bind_accel('filelist', 'activate/location', 'Activate location bar',
        '<ctrl>l', FileList.activate_location)

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
        return self.places.get(path, (None, None))

    def back(self):
        if self.current > 1:
            self.current -= 1
            path = self.hline[self.current-1]
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
    def __init__(self, clipboard):
        self.clipboard = clipboard
        self.model = gtk.ListStore(gtk.gdk.Pixbuf, str, gio.FileInfo, bool)

        self.widget = gtk.VBox()

        self.uri_entry = gtk.Entry()
        self.uri_entry.connect('activate', self.on_uri_entry_activate)
        self.widget.pack_start(self.uri_entry, False, False)

        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.widget.pack_start(self.sw)

        self.view = view = FmdIconView()
        view.connect('item-activated', self.on_item_activated)

        icon_cell = gtk.CellRendererPixbuf()
        view.icon_renderer = icon_cell
        view.set_attributes(icon_cell, pixbuf=0, sensitive=3)
        icon_cell.props.follow_state = True
        icon_cell.props.xpad = 1

        text_cell = gtk.CellRendererText()
        view.text_renderer = text_cell
        view.set_attributes(text_cell, text=1, sensitive=3)

        self.sw.add(view)

        self.isearch = InteractiveSearch(self._search)
        self.isearch.attach(view)

        self.icon_cache = {}
        self.current_folder = None
        self.history = History()
        self.show_hidden = False

    def _search(self, text, direction, skip):
        idx = sidx = self.view.get_cursor()[0] if self.view.get_cursor() else 0

        if skip:
            idx = (sidx + direction) % len(self.model)
        else:
            sidx = (sidx - 1) % len(self.model)

        while sidx != idx:
            r = self.model[idx]
            if r[1].lower().startswith(text):
                self.view.set_cursor((idx,))
                break

            idx = (idx + direction) % len(self.model)
        else:
            if not skip:
                self.view.unselect_all()

    def set_uri(self, uri, add_to_history=True, cursor=None, scroll=None):
        self.uri_entry.set_text(uri)
        self.update(uri, add_to_history, cursor, scroll)

    def update(self, uri, add_to_history=True, cursor=None, scroll=None):
        self.view.grab_focus()
        self.fill(uri, add_to_history, cursor, scroll)

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

    def fill(self, uri, add_to_history=True, cursor=None, scroll=None):
        self.view.set_model(None)

        if self.current_folder:
            self.history.update(self.current_folder.get_path(), self.view.get_cursor(),
                self.sw.props.hadjustment.value)


        self.current_folder = gio.file_parse_name(uri)
        enumerator = self.current_folder.enumerate_children('standard::*')

        infos = []
        while True:
            fi = enumerator.next_file()
            if not fi:
                break

            if not self.show_hidden and fi.get_attribute_boolean('standard::is-hidden'):
                continue

            content_type = fi.get_attribute_as_string('standard::content-type')
            sk = 0 if content_type == 'inode/directory' else 1
            name = fi.get_attribute_as_string('standard::display-name')
            infos.append((sk, name.lower(), name, fi))

        enumerator.close()

        self.model.clear()
        for _, _, name, info in sorted(infos):
            self.model.append((self.get_pixbuf(info), name, info, True))

        if cursor:
            self.view.set_cursor(cursor)
        else:
            self.view.set_cursor((0,))

        self.view.set_model(self.model)
        self.view.queue_draw()

        if add_to_history:
            self.history.add(self.current_folder.get_path())

    def on_uri_entry_activate(self, entry):
        self.update(entry.get_text())

    def on_item_activated(self, view, path):
        row = self.model[path]
        fi = row[2]
        ft = fi.get_file_type()
        cfile = self.current_folder.get_child_for_display_name(row[1])

        if ft == gio.FILE_TYPE_DIRECTORY:
            self.set_uri(cfile.get_path())
        elif ft == gio.FILE_TYPE_REGULAR:
            app_info = gio.app_info_get_default_for_type(fi.get_content_type(), False)
            if app_info:
                os.chdir(self.current_folder.get_path())
                app_info.launch([cfile])

    def navigate_parent(self):
        parent = self.current_folder.get_parent()
        if parent:
            uri = parent.get_path()
            cursor, scroll = self.history.get(uri)
            self.set_uri(uri, True, cursor, scroll)

    def navigate_back(self):
        path, cursor, scroll = self.history.back()
        if path:
            self.set_uri(path, False, cursor, scroll)

    def navigate_forward(self):
        path, cursor, scroll = self.history.forward()
        if path:
            self.set_uri(path, False, cursor, scroll)

    def activate_location(self):
        self.uri_entry.grab_focus()

    def show_hidden(self):
        self.show_hidden = not self.show_hidden
        self.fill(self.current_folder.get_path(), False)

    def cut(self):
        print 'cut'

    def copy(self):
        print 'copy'

    def paste(self):
        print 'paste'

    def delete(self):
        print 'delete'

    def force_delete(self):
        print 'fdelete'