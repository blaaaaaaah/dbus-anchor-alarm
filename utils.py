from traceback import print_exc
from os import _exit as os_exit

# copy/paste from velib_utils. Not using velib_utils because of dependencies on dbus when testing locally

# Use this function to make sure the code quits on an unexpected exception. Make sure to use it
# when using GLib.idle_add and also GLib.timeout_add.
# Without this, the code will just keep running, since GLib does not stop the mainloop on an
# exception.
# Example: GLib.idle_add(exit_on_error, myfunc, arg1, arg2)
def exit_on_error(func, *args, **kwargs):
	try:
		return func(*args, **kwargs)
	except:
		try:
			print ('exit_on_error: there was an exception. Printing stacktrace will be tried and then exit')
			print_exc()
		except:
			pass

		# sys.exit() is not used, since that throws an exception, which does not lead to a program
		# halt when used in a dbus callback, see connection.py in the Python/Dbus libraries, line 230.
		os_exit(1)





def handle_stdin(command_callback):
    import sys
    import os
    import signal 
    from gi.repository import GLib
    
    loop = GLib.MainLoop()

    def process_std_in(source, condition):
        if condition == GLib.IO_IN:
            line = source.readline().strip()    
            line = line.strip()
            if not line:
                return 

            if ":" in line:
                command, text = line.split(":", 1)
            else:
                command, text = line, None

            if command == "exit":
                loop.quit()
            else:
                command_callback(command, text)

        return True

    signal.signal(signal.SIGINT, lambda source,cond: loop.quit())

    GLib.io_add_watch(sys.stdin, GLib.IO_IN, process_std_in)

    try:
        loop.run()
    except KeyboardInterrupt:
        pass
