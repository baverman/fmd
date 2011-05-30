import glib
import gio

NONE_CALLBACK = lambda *args: None

class Executor(object):
    def __init__(self):
        self.job_queue = []
        self.is_run = False
        self.cancel = gio.Cancellable()

    def job_done(self, source, result, moved):
        source.copy_finish(result)
        if moved:
            source.delete()

        glib.idle_add(self.idle)

    def job_move(self, source, target):
        source.copy_async(target, self.job_done, NONE_CALLBACK, gio.FILE_COPY_NOFOLLOW_SYMLINKS,
            cancellable=self.cancel, user_data=True)

    def job_move_dir(self, source, target):
        pass

    def job_copy(self, source, target):
        source.copy_async(target, self.job_done, NONE_CALLBACK, gio.FILE_COPY_NOFOLLOW_SYMLINKS,
            cancellable=self.cancel, user_data=False)

    def idle(self):
        try:
            job = self.job_queue.pop(0)
        except IndexError:
            self.is_run = False
            return False

        job[0](*job[1:])
        return False

    def check_and_run(self):
        if not self.is_run:
            self.is_run = True
            glib.idle_add(self.idle)

    def copy(self, filelist, target):
        for f in filelist:
            fi = f.query_info('standard::type', gio.FILE_QUERY_INFO_NOFOLLOW_SYMLINKS)
            tf = target.get_child(f.get_basename())
            self.push_copy_task(f, tf, fi.get_file_type())

        self.check_and_run()

    def push_copy_task(self, source, target, source_type=None):
        if not source_type:
            source_type = source.query_info('standard::type',
                gio.FILE_QUERY_INFO_NOFOLLOW_SYMLINKS).get_file_type()

        if source_type == gio.FILE_TYPE_DIRECTORY:
            self.job_queue.append((None, source, target))
        else:
            self.job_queue.append((self.job_copy, source, target))

    def push_move_task(self, source, target, source_type=None):
        if not source_type:
            source_type = source.query_info('standard::type',
                gio.FILE_QUERY_INFO_NOFOLLOW_SYMLINKS).get_file_type()

        if source_type == gio.FILE_TYPE_DIRECTORY:
            self.job_queue.append((self.job_move_dir, source, target))
        else:
            self.job_queue.append((self.job_move, source, target))

    def move(self, filelist, target):
        target_fs = target.query_info('id::filesystem').get_attribute_as_string('id::filesystem')
        for f in filelist:
            if target.equal(f.get_parent()):
                continue

            fi = f.query_info('standard::type,id::filesystem', gio.FILE_QUERY_INFO_NOFOLLOW_SYMLINKS)
            source_fs = fi.get_attribute_as_string('id::filesystem')

            tf = target.get_child(f.get_basename())
            if source_fs == target_fs:
                f.move(tf, NONE_CALLBACK, gio.FILE_COPY_NOFOLLOW_SYMLINKS)
            else:
                self.push_move_task(f, tf, fi.get_file_type())

        self.check_and_run()

    def cancel(self):
        pass