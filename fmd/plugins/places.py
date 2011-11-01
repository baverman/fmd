import gio, os.path, glib

from uxie.misc import BuilderAware
from uxie.utils import join_to_file_dir
from uxie.actions import Activator

dialog = [None]

def init(injector):
    injector.bind_accel('filelist', 'show-places', 'Window/_Places#20', '<alt>p', show_places)

def show_places(filelist):
    if not dialog[0]:
        dialog[0] = Places()

    dialog[0].show(filelist)

class Places(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'places.glade'))

        from fmd.app import keymap
        self.activator = keymap.get_activator(self.window)
        self.activator.bind_accel('window', 'escape', '_Close', 'Escape', self.on_window_delete_event)

        self.view.realize()

    def add(self, uri):
        info = gio.file_parse_name(uri).query_info('standard::display-name,standard::icon')
        title = info.get_display_name()
        pixbuf = self.filelist.get_pixbuf(info)
        self.model.append((title, uri, pixbuf))

    def show(self, filelist):
        self.filelist = filelist

        self.view.set_model(None)
        self.model.clear()

        self.add(os.path.expanduser('~'))
        self.add(glib.get_user_special_dir(glib.USER_DIRECTORY_DESKTOP))
        self.add('trash:///')
        self.add('computer:///root.link')
        self.add('network:///')

        for l in open('/home/bobrov/.gtk-bookmarks'):
            self.add(l.strip())

        self.view.set_model(self.model)

        self.view.set_cursor((0,))

        w, h = self.view.size_request()
        if h != 0:
            self.sw.set_size_request(-1, max(200, min(h + 5, 300)))

        self.window.resize(*self.window.size_request())
        self.window.set_transient_for(filelist.view.get_toplevel())
        self.window.show()

    def on_view_row_activated(self, view, path, column):
        self.window.hide()
        self.filelist.set_uri(self.model[path][1])

    def on_window_delete_event(self, *args):
        self.window.hide()
        return True
