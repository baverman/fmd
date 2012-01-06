def init(injector):
    injector.add_context('sync-names', 'filelist-active', context)
    injector.bind('sync-names', 'sync-names', '_Utils/_Sync names', sync_names).to('<ctrl>s')

def context(filelist):
    return filelist if len(filelist.model.selection) == 2 else None

def split(filename):
    name, sep, ext = filename.rpartition('.')
    if sep:
        if name:
            return name, '.' + ext
        else:
            return filename, ''
    else:
        return ext, ''

def sync_names(filelist):
    fi1, fi2 = [filelist.model[r][2] for r in filelist.model.selection]
    if fi1.get_size() > fi2.get_size():
        fi1, fi2 = fi2, fi1

    (name1, ext1), (name2, ext2) = [split(r.get_display_name()) for r in (fi1, fi2)]

    if ext1 == ext2:
        filelist.feedback.show('Filenames have same extensions', 'warn')
        return

    source = filelist.current_folder.get_child(fi1.get_name())
    target = filelist.current_folder.get_child_for_display_name(name2 + ext1)

    source.move(target)

    filelist.fill()
    filelist.view.set_cursor(filelist.get_cursor_for_name(fi2.get_display_name()))
    filelist.view.refresh(False)

    filelist.feedback.show('Synced', 'done')
