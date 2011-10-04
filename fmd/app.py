import gtk

from uxie.actions import Activator
from uxie.floating import Manager as FeedbackManager
from uxie.plugins import Manager as PluginManager

import filelist
import clipboard
import fsutils

class App(object):
    def __init__(self):
        self.wg = gtk.WindowGroup()
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(700, 415)
        self.window.connect('delete-event', self.quit)
        self.wg.add_window(self.window)

        self.clipboard = clipboard.Clipboard()
        self.window.feedback = self.feedback = FeedbackManager()

        self.activator = Activator()
        self.activator.add_context('filelist', None, lambda: self.filelist)
        self.activator.map(None, 'copy', '<ctrl>c')
        self.activator.map(None, 'copy', '<ctrl>Insert')
        self.activator.map(None, 'cut', '<ctrl>x')
        self.activator.map(None, 'cut', '<shift>Delete')
        self.activator.map(None, 'paste', '<ctrl>v')
        self.activator.map(None, 'paste', '<shift>Insert')
        self.activator.map(None, 'delete', 'Delete')

        self.activator.bind_accel('window', 'quit', '$_Quit', '<ctrl>q', self.quit)
        self.activator.bind_accel('window', 'close-window',
            '_Window/_Close', '<ctrl>w', self.quit)

        self.pm = PluginManager(self.activator)

        filelist.init(self.activator)
        self.init_plugins(self.pm)
        self.activator.attach(self.window)

        self.executor = fsutils.Executor()

        self.filelist = filelist.FileList(self.clipboard, self.executor)
        self.window.add(self.filelist.widget)
        self.pm.ready('filelist', self.filelist)

    def init_plugins(self, pm):
        from plugins import sync_names, places, info, history
        pm.add_plugin(sync_names)
        pm.add_plugin(places)
        pm.add_plugin(info)
        pm.add_plugin(history)

    def open(self, uri):
        self.window.show_all()
        self.filelist.set_uri(uri)

    def quit(self, *args):
        gtk.main_quit()