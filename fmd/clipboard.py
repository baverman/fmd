import gtk

TARGET = 'fmd/files'

class Clipboard(object):
    def get_clipboard(self):
        return gtk.clipboard_get()

    def is_empty(self):
        targets = self.get_clipboard().wait_for_targets()
        return not targets or TARGET not in targets

    def _get_func(self, clipboard, selectiondata, info, data):
        is_cut, file_list = data
        if info == 0:
            selectiondata.set(TARGET, 8, str((is_cut, [r.get_uri() for r in file_list])))
        elif info == 1:
            selectiondata.set_text(' '.join(r.get_path() for r in file_list), -1)

    def _clear_func(self, clipboard, data):
        pass

    def _set_data(self, is_cut, files):
        cb = self.get_clipboard()
        cb.set_with_data([(TARGET, 0, 0), ('STRING', 0, 1)],
            self._get_func, self._clear_func, (is_cut, files))

    def copy(self, files):
        self._set_data(False, files)

    def cut(self, files):
        self._set_data(True, files)

    def _paste_callback(self, clipboard, selection, callback):
        is_cut, files = eval(selection.data)
        if is_cut:
            clipboard.clear()

        callback(is_cut, files)

    def paste(self, callback):
        if not self.is_empty():
            cb = self.get_clipboard()
            cb.request_contents('fmd/files', self._paste_callback, callback)