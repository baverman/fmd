import gtk

from uxie.actions import Activator, ContextActivator

import filelist

class App(object):
    def __init__(self):
        self.wg = gtk.WindowGroup()
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(700, 415)
        self.window.connect('destroy', self.quit)
        self.wg.add_window(self.window)

        self.filelist = filelist.FileList()
        self.window.add(self.filelist.widget)

        self.activator = Activator()
        self.activator.bind_accel('application/quit', 'Quit', '<ctrl>q', self.quit)
        self.activator.bind_accel('window/close', 'Close window', '<ctrl>w', self.quit)
        self.activator.attach(self.window)

        self.context_activator = ContextActivator(self)
        filelist.init(self.context_activator)
        self.context_activator.attach(self.window)

    def open(self, uri):
        self.window.show_all()
        self.filelist.set_uri(uri)

    def quit(self, *args):
        gtk.main_quit()

    def get_context(self, window):
        return 'filelist', self.filelist