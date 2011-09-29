import gio

from uxie.misc import BuilderAware
from uxie.actions import Activator
from uxie.utils import join_to_file_dir

def init(injector):
    injector.bind_accel('filelist', 'show-history', 'Show history browser',
        '<alt>e', show_history)


history_browser = [None]

def show_history(filelist):
    if filelist.history.is_empty():
        filelist.feedback.show('History is empty', 'warn')
        return

    h = history_browser[0]
    if not h:
        h = history_browser[0] = HistoryViewer()

    h.show(filelist, filelist.history)


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