import gtk

from uxie.utils import human_size

def init(activator, pm):
    pm.on_ready('filelist', filelist_ready)

    activator.bind_accel('filelist-with-selected-files', 'show-info', 'Show info box',
        '<alt>i', show_info)

def filelist_ready(filelist):
    filelist.model.connect('selection-changed', on_selection_changed)


def fill_widget(widget, model, selection):
    size = sum(model[r][2].get_size() for r in selection)
    widget.set_text('Size of selected file(s)\n%s' % human_size(size))

def on_selection_changed(model, selection):
    feedback = info_bar[0]
    if feedback:
        fill_widget(feedback.widget, model, selection)

info_bar = [None]

def show_info(filelist):
    feedback = info_bar[0]
    if feedback:
        if feedback.is_active():
            feedback.cancel()
            info_bar[0] = None
            return

    widget = gtk.Label()
    widget.set_padding(10, 5)
    widget.set_justify(gtk.JUSTIFY_RIGHT)

    fill_widget(widget, filelist.model, filelist.model.selection)

    feedback = filelist.feedback.show_widget(widget)
    info_bar[0] = feedback
