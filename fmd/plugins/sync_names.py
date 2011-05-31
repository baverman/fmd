def init(activator):
    activator.add_context('sync-names', 'filelist-active', context)

    activator.bind_accel('sync-names', 'sync-names', 'Synchronize filenames',
        '<ctrl>s', sync_names)

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
    filelist.view.refresh()
    filelist.feedback.show('Synced', 'done')
