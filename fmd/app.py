import gtk

from uxie.utils import join_to_settings_dir
from uxie.actions import KeyMap
from uxie.floating import Manager as FeedbackManager
from uxie.plugins import Manager as PluginManager

import filelist
import clipboard
import fsutils

keymap = KeyMap(join_to_settings_dir('fmd', 'keys.conf'))
keymap.map_generic('root-menu', 'F1')
keymap.map_generic('copy', '<ctrl>c')
keymap.map_generic('copy', '<ctrl>Insert')
keymap.map_generic('cut', '<ctrl>x')
keymap.map_generic('cut', '<shift>Delete')
keymap.map_generic('paste', '<ctrl>v')
keymap.map_generic('paste', '<shift>Insert')
keymap.map_generic('delete', 'Delete')

class App(object):
    def __init__(self):
        self.wg = gtk.WindowGroup()
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(700, 415)
        self.window.connect('delete-event', self.quit)
        self.wg.add_window(self.window)

        self.clipboard = clipboard.Clipboard()
        self.window.feedback = self.feedback = FeedbackManager()

        self.activator = keymap.get_activator(self.window, 'main_window')
        self.activator.add_context('filelist', None, lambda: self.filelist)

        self.activator.bind_menu('_File#1')
        self.activator.bind_menu('_View#10')
        self.activator.bind_menu('_Goto#20')
        self.activator.bind_menu('_Run#30').to('<Alt>X')
        self.activator.bind_menu('_Utils#40')
        self.activator.bind_menu('_Window#50')

        self.activator.bind('window', 'quit', 'File/_Quit#100', self.quit).to('<ctrl>q')
        self.activator.bind('window', 'close-window', 'Window/_Close#100', self.quit).to('<ctrl>w')

        self.pm = PluginManager(self.activator)

        filelist.init(self.activator)
        self.init_plugins(self.pm)

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