import gtk

from .filelist import FileList

class App(object):
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(600, 400)
        self.window.connect('destroy', self.quit)

        self.filelist = FileList()
        self.window.add(self.filelist.widget)

    def start(self, uri):
        self.window.show_all()
        self.filelist.set_uri(uri)

    def quit(self, window):
        gtk.main_quit()