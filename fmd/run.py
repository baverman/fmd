def run():
    import sys, os

    try:
        uri = sys.argv[1]
    except IndexError:
        uri = os.getcwd()


    import gtk
    from .app import App
    from uxie.utils import idle

    application = App()
    idle(application.open, uri)

    gtk.main()
