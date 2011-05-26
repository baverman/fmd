import gtk

FMD_COPY = 0
FMD_CUT = 1

class Clipboard(object):
    def __init__(self):
        self.files = []
        self.is_cutted = False

    def get_clipboard(self):
        return gtk.clipboard_get()

    def is_empty(self):
        return len(self.files) == 0

    def _get_func(self, clipboard, selectiondata, info, data):
        selectiondata.set_uris([r.get_uri for r in self.files])

    def _clear_func(self, clipboard, data):
        pass

    def copy(self, files):
        self.files[:] = files
        self.is_cutted = False
        cb = self.get_clipboard()
        cb.set_with_data([('fmd/files', 0, 0)], self._get_func, self._clear_func, None)

    def cut(self, files):
        self.files[:] = files
        self.is_cutted = True
        cb = self.get_clipboard()
        cb.set_with_data([('fmd/files', 0, 0)], self._get_func, self._clear_func, None)

    def paste(self, target_dir):
        self.files[:] = []
        self.is_cutted = False