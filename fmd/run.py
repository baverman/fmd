def run():
    import sys, os.path

    try:
        uri = sys.argv[1]
    except IndexError:
        uri = os.path.expanduser('~')


    import gtk
    from .app import App
    from uxie.utils import idle

    application = App()
    idle(application.open, uri)

    gtk.main()
