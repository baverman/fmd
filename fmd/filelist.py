import os
import gtk
import gio

from uxie.search import InteractiveSearch
from uxie.tree import SelectionListStore
from uxie.misc import BuilderAware
from uxie.utils import join_to_file_dir, idle
from uxie.actions import Activator

from .iconview import FmdIconView

def init(activator):
    with activator.on('filelist') as ctx:
        ctx.bind_accel('view/hidden', 'Toggle hidden files',
            '<ctrl>h', FileList.show_hidden)

        ctx.bind('paste', 'Paste', FileList.paste)

        ctx.bind_accel('activate/location', 'Activate location bar',
            '<ctrl>l', FileList.activate_location)

        ctx.bind_accel('history-browser', 'Show history browser',
            '<alt>e', FileList.show_history)

    with activator.on('filelist_active') as ctx:
        ctx.bind_accel('navigate/parent', 'Navigate to parent directory',
            '<alt>Up', FileList.navigate_parent)

        ctx.bind_accel('navigate/back', 'Navigate back in history',
            '<alt>Left', FileList.navigate_back)
        ctx.map('navigate/back', 'BackSpace')

        ctx.bind_accel('navigate/forward', 'Navigate forward in history',
            '<alt>Right', FileList.navigate_forward)

    with activator.on('filelist_with_selected_files') as ctx:
        ctx.bind('copy', 'Copy', FileList.copy)
        ctx.bind('cut', 'Cut', FileList.cut)
        ctx.bind_accel('delete', 'Delete', 'Delete', FileList.delete)
        ctx.bind_accel('force-delete', 'Force delete',
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

    def fill(self, uri, add_to_history=True, cursor=None, scroll=None):
        self.view.set_model(None)

        if self.current_folder:
            self.history.update(self.current_folder.get_path(), self.view.get_cursor(),
                self.sw.props.hadjustment.value)


        self.current_folder = gio.file_parse_name(uri)
        enumerator = self.current_folder.enumerate_children('standard::*')

        self.setup_monitor(self.current_folder)

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
        self.view.refresh(False)

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
        self.window.realize()

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

        def setup_model(path):
            f = gio.File(path=path)

            try:
                parent_path = f.get_parent().get_path()
            except AttributeError:
                parent_path = None

            try:
                parent_iter = parents[parent_path]
            except KeyError:
                setup_model(parent_path)
                parent_iter = parents[parent_path]

            fname = f.query_info(gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME).get_display_name()
            parents[path] = self.model.append(parent_iter, (fname, p))

        for p in sorted(history.places, key=lambda r: r.lower()):
            if p not in parents:
                setup_model(p)

        self.view.set_model(self.model)
        self.view.expand_all()

        w, h = self.view.size_request()
        self.sw.set_size_request(-1, max(100, min(h + 5, 300)))

        self.window.resize(*self.window.size_request())
        self.window.set_transient_for(filelist.view.get_toplevel())
        self.window.show()