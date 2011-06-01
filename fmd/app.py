import gtk

from uxie.actions import Activator, ContextActivator
from uxie.feedback import TextFeedback, FeedbackManager, FeedbackHelper
from uxie.plugins import Manager as PluginManager

import filelist
import clipboard
import fsutils

class App(object):
    def __init__(self):
        self.wg = gtk.WindowGroup()
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(700, 415)
        self.window.connect('destroy', self.quit)
        self.wg.add_window(self.window)

        self.clipboard = clipboard.Clipboard()
        self.feedback = FeedbackManager()
        self.window.feedback = FeedbackHelper(self.feedback, self.window)

        self.activator = Activator()
        self.activator.bind_accel('application/quit', 'Quit', '<ctrl>q', self.quit)
        self.activator.bind_accel('window/close', 'Close window', '<ctrl>w', self.quit)
        self.activator.attach(self.window)

        self.context_activator = ContextActivator()
        self.context_activator.add_context('filelist', None, lambda: self.filelist)
        self.context_activator.map(None, 'copy', '<ctrl>c')
        self.context_activator.map(None, 'copy', '<ctrl>Insert')
        self.context_activator.map(None, 'cut', '<ctrl>x')
        self.context_activator.map(None, 'cut', '<shift>Delete')
        self.context_activator.map(None, 'paste', '<ctrl>v')
        self.context_activator.map(None, 'paste', '<shift>Insert')
        self.context_activator.map(None, 'delete', 'Delete')

        self.pm = PluginManager(self.context_activator)

        filelist.init(self.context_activator)
        self.init_plugins(self.pm)
        self.context_activator.attach(self.window)

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

    def show_feedback(self, text, category='info'):
        self.feedback.add_feedback(self.window, TextFeedback(text, category))