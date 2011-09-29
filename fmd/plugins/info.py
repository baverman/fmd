import gtk

from uxie.utils import human_size

def init(injector):
    injector.on_ready('filelist', filelist_ready)

    injector.bind_accel('filelist-with-selected-files', 'show-info', 'Show info box',
        '<alt>i', show_info)

def filelist_ready(filelist):
    filelist.model.connect('selection-changed', on_selection_changed)

def fill_widget(widget, model, selection):
    size = sum(model[r][2].get_size() for r in selection)
    widget.set_text('Size of selected file(s)\n%s' % human_size(size))

def on_selection_changed(model, selection):
    feedback = info_bar[0]
    if feedback:
        fill_widget(feedback.label, model, selection)

info_bar = [None]

def show_info(filelist):
    feedback = info_bar[0]
    if feedback:
        if feedback.is_active():
            feedback.cancel()
            info_bar[0] = None
            return

    widget = gtk.EventBox()
    frame = gtk.Frame()
    widget.add(frame)

    label = gtk.Label()
    label.set_padding(10, 5)
    label.set_justify(gtk.JUSTIFY_RIGHT)
    frame.add(label)

    fill_widget(label, filelist.model, filelist.model.selection)

    feedback = filelist.feedback.show_widget(widget)
    feedback.label = label
    info_bar[0] = feedback
