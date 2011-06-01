import os
import gtk
import gio

from uxie.search import InteractiveSearch
from uxie.tree import SelectionListStore
from uxie.misc import BuilderAware
from uxie.utils import join_to_file_dir
from uxie.actions import Activator

from .iconview import FmdIconView

def init(activator):
    activator.add_context('filelist-active', 'filelist',
        lambda f: f if f.view.has_focus() else None)

    activator.add_context('filelist-with-selected-files', 'filelist-active',
        lambda f: f if f.model.selection else None)

    activator.add_context('filelist-show-hidden', 'filelist',
        lambda f: f if f.show_hidden else None)

    activator.add_context('filelist-hide-hidden', 'filelist',
        lambda f: f if not f.show_hidden else None)

    activator.bind_accel('filelist-show-hidden', 'hide-hidden',
        'Do not show hidden files', '<ctrl>h', FileList.show_hidden)

    activator.bind_accel('filelist-hide-hidden', 'show-hidden',
        'Show hidden files', '<ctrl>h', FileList.show_hidden)

    with activator.on('filelist') as ctx:
        ctx.bind('paste', 'Paste', FileList.paste)

        ctx.bind_accel('focus-location', 'Activate location bar',
            '<ctrl>l', FileList.activate_location)

        ctx.bind_accel('show-history', 'Show history browser',
            '<alt>e', FileList.show_history)

    with activator.on('filelist-active') as ctx:
        ctx.bind_accel('goto-parent', 'Navigate to parent directory',
            '<alt>Up', FileList.navigate_parent)

        ctx.bind_accel('back', 'Navigate back in history',
            '<alt>Left', FileList.navigate_back)
        ctx.map('back', 'BackSpace')

        ctx.bind_accel('forward', 'Navigate forward in history',
            '<alt>Right', FileList.navigate_forward)

    with activator.on('filelist-with-selected-files') as ctx:
        ctx.bind('copy', 'Copy', FileList.copy)
        ctx.bind('cut', 'Cut', FileList.cut)
        ctx.bind('delete', 'Delete', FileList.delete)
        ctx.bind_accel('delete-permanently', 'Force delete',
            '<shift>Delete', FileList.force_delete, 10)


class History(object):
    def __init__(self):
        self.places = {}
        self.hline = []
        self.current = 0

    def is_empty(self):
        return not self.places

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
    def __init__(self, clipboard, executor):
        self.clipboard = clipboard
        self.executor = executor

        self.model = SelectionListStore(gtk.gdk.Pixbuf, str, gio.FileInfo, bool)

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

        self.monitor = None

    @property
    def feedback(self):
        return self.view.get_toplevel().feedback

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
        folder = gio.file_parse_name(uri)
        file_info = folder.query_info('standard::*')
        ft = file_info.get_file_type()

        if ft == gio.FILE_TYPE_DIRECTORY:
            uri = folder.get_path() or folder.get_uri()
        elif ft in (gio.FILE_TYPE_MOUNTABLE, gio.FILE_TYPE_SHORTCUT):
            uri = file_info.get_attribute_as_string(gio.FILE_ATTRIBUTE_STANDARD_TARGET_URI)
            folder = gio.File(uri=uri)
        else:
            raise Exception('Unknown file type %s %s' % (ft, folder.get_uri()))

        self.uri_entry.set_text(uri)

        if self.current_folder:
            self.history.update(self.current_folder.get_uri(), self.view.get_cursor(),
                self.sw.props.hadjustment.value)

        self.current_folder = folder
        self.setup_monitor(folder)

        self.fill()
        self.view.grab_focus()

        if cursor:
            self.view.set_cursor(cursor)
        else:
            self.view.set_cursor((0,))

        self.view.refresh(False)

        if add_to_history:
            self.history.add(folder.get_uri())

    def get_pixbuf(self, info):
        key = info.get_icon()

        try:
            return self.icon_cache[key]
        except KeyError:
            pass

        theme = gtk.icon_theme_get_default()
        icon_info = theme.lookup_by_gicon(key, 16, 0)

        if not icon_info:
            icon_info = theme.lookup_icon('gtk-file', 16, 0)

        if icon_info:
            pixbuf = icon_info.load_icon()
        else:
            pixbuf = None

        self.icon_cache[key] = pixbuf
        return pixbuf

    def setup_monitor(self, file):
        if self.monitor:
            self.monitor.cancel()

        self.monitor = file.monitor()
        self.monitor.connect('changed', self.on_file_change)

    def get_info_for_file_which_will_change_model(self, file):
        if not self.current_folder.equal(file.get_parent()):
            return None

        fi = file.query_info('standard::*')
        if not self.show_hidden and fi.get_is_hidden():
            return None

        return fi

    def add_file(self, file):
        fi = self.get_info_for_file_which_will_change_model(file)
        self.model.append((self.get_pixbuf(fi), fi.get_display_name(), fi, True))
        self.view.refresh()

    def remove_file(self, file):
        if not self.current_folder.equal(file.get_parent()):
            return None

        for r in self.model:
            if r[2].get_name() == file.get_basename():
                del self.model[r.path]
                break

        self.view.refresh()

    def on_file_change(self, monitor, file, other_file, event_type):
        if event_type == gio.FILE_MONITOR_EVENT_CREATED:
            self.add_file(file)
        elif event_type == gio.FILE_MONITOR_EVENT_DELETED:
            self.remove_file(file)
        elif event_type == gio.FILE_MONITOR_EVENT_MOVED:
            self.remove_file(file)
            self.add_file(other_file)

    def fill(self):
        self.view.set_model(None)

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

        self.view.set_model(self.model)

    def on_uri_entry_activate(self, entry):
        self.set_uri(entry.get_text())

    def set_uri_from_file_info(self, file_info, cfile):
        ft = file_info.get_file_type()

        if ft == gio.FILE_TYPE_DIRECTORY:
            self.set_uri(cfile.get_path() or cfile.get_uri())
        elif ft in (gio.FILE_TYPE_MOUNTABLE, gio.FILE_TYPE_SHORTCUT):
            uri = file_info.get_attribute_as_string(gio.FILE_ATTRIBUTE_STANDARD_TARGET_URI)
            self.set_uri(uri)
        elif ft == gio.FILE_TYPE_REGULAR:
            app_info = cfile.query_default_handler()
            if app_info:
                os.chdir(self.current_folder.get_path())
                app_info.launch([cfile])
        else:
            print ft, cfile.get_uri()

    def on_item_activated(self, view, path):
        row = self.model[path]
        fi = row[2]
        cfile = self.current_folder.get_child(fi.get_name())
        ft = fi.get_file_type()
        if ft == gio.FILE_TYPE_REGULAR:
            app_info = gio.app_info_get_default_for_type(fi.get_content_type(), False)
            if app_info:
                os.chdir(self.current_folder.get_path())
                app_info.launch([cfile])
        else:
            self.set_uri(cfile.get_uri())

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
        self.fill()

    def get_filelist_from_selection(self):
        result = []
        for path in self.model.selection:
            result.append(self.current_folder.get_child_for_display_name(
                self.model[path][1]))

        return result

    def cut(self):
        filelist = self.get_filelist_from_selection()
        self.clipboard.cut(filelist)

        for r in self.model:
            r[3] = r.path not in self.model.selection
        self.view.queue_draw()
        self.feedback.show('Cut')

    def copy(self):
        filelist = self.get_filelist_from_selection()
        self.clipboard.copy(filelist)

        for r in self.model:
            r[3] = True

        self.view.refresh(False)
        self.feedback.show('Copied')

    def paste(self):
        def on_paste(is_cut, filelist):
            filelist = [gio.File(uri=r) for r in filelist]
            if is_cut:
                self.executor.move(filelist, self.current_folder)
                for r in self.model:
                    r[3] = True
                self.view.refresh(False)
            else:
                self.executor.copy(filelist, self.current_folder)

        self.clipboard.paste(on_paste)


    def delete(self):
        files = self.get_filelist_from_selection()
        try:
            for f in files:
                f.trash()
        except gio.Error, e:
            self.feedback.show(str(e), 'error')
        else:
            if len(files) == 1:
                msg = 'File deletion was requested'
            else:
                msg = 'Deletion of selected files was requested'

            self.feedback.show(msg, 'info')

    def force_delete(self):
        import time
        df = getattr(self, 'force_delete_feedback', None)
        if df and df.is_active() and time.time() - df.start < 1:
            df.cancel()
            files = self.get_filelist_from_selection()
            try:
                for f in files:
                    f.delete()
            except gio.Error, e:
                self.feedback.show(str(e), 'error')
            else:
                if len(files) == 1:
                    msg = 'File deletion was requested'
                else:
                    msg = 'Deletion of selected files was requested'

                self.feedback.show(msg, 'info')
        else:
            if df: df.cancel()
            self.force_delete_feedback = self.feedback.show(
                'Files will be deleted permanently', 'warn', 3000)

    def show_history(self):
        if self.history.is_empty():
            self.feedback.show('History is empty', 'warn')
            return

        try:
            h = self.history_browser
        except AttributeError:
            h = self.history_browser = HistoryViewer()

        h.show(self, self.history)


class HistoryViewer(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'history.glade'))
        self.view.realize()

        self.activator = Activator()
        self.activator.bind_accel('escape', 'Close window', 'Escape', self.on_window_delete_event)
        self.activator.attach(self.window)

    def on_window_delete_event(self, *args):
        self.window.hide()
        return True

    def on_view_row_activated(self, view, path, column):
        try:
            row = self.model[path]
        except IndexError:
            return

        self.window.hide()
        self.filelist.set_uri(row[1])

    def show(self, filelist, history):
        self.filelist = filelist
        self.view.set_model(None)
        self.model.clear()

        parents = {None:None}

        def setup_model(uri):
            f = gio.File(uri=uri)

            try:
                parent_path = f.get_parent().get_uri()
            except AttributeError:
                parent_path = None

            try:
                parent_iter = parents[parent_path]
            except KeyError:
                setup_model(parent_path)
                parent_iter = parents[parent_path]

            fname = f.query_info(gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME).get_display_name()
            parents[uri] = self.model.append(parent_iter, (fname, uri))

        for u in sorted(history.places, key=lambda r: r.lower()):
            if u not in parents:
                setup_model(u)

        self.view.set_model(self.model)
        self.view.expand_all()

        w, h = self.view.size_request()
        self.sw.set_size_request(-1, max(100, min(h + 5, 300)))

        self.window.resize(*self.window.size_request())
        self.window.set_transient_for(filelist.view.get_toplevel())
        self.window.show()