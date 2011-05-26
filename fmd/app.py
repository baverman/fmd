import gtk

from uxie.actions import Activator, ContextActivator

import filelist
import clipboard

class App(object):
    def __init__(self):
        self.wg = gtk.WindowGroup()
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(700, 415)
        self.window.connect('destroy', self.quit)
        self.wg.add_window(self.window)

        self.clipboard = clipboard.Clipboard()

        self.filelist = filelist.FileList(self.clipboard)
        self.window.add(self.filelist.widget)

        self.activator = Activator()
        self.activator.bind_accel('application/quit', 'Quit', '<ctrl>q', self.quit)
        self.activator.bind_accel('window/close', 'Close window', '<ctrl>w', self.quit)
        self.activator.attach(self.window)

        self.context_activator = ContextActivator(self)
        self.context_activator.map(None, 'copy', '<ctrl>c')
        self.context_activator.map(None, 'copy', '<ctrl>Insert')
        self.context_activator.map(None, 'cut', '<ctrl>x')
        self.context_activator.map(None, 'cut', '<shift>Delete')
        self.context_activator.map(None, 'paste', '<ctrl>v')
        self.context_activator.map(None, 'paste', '<shift>Insert')

        filelist.init(self.context_activator)
        self.context_activator.attach(self.window)

    def open(self, uri):
        self.window.show_all()
        self.filelist.set_uri(uri)

    def quit(self, *args):
        gtk.main_quit()

    def get_context(self, window, ctx):
        if ctx == 'filelist':
            return self.filelist
        elif ctx == 'filelist_active' and self.filelist.view.has_focus():
            return self.filelist
        elif ctx == 'filelist_with_selected_files' and self.filelist.view.selected:
            return self.filelist

        return None