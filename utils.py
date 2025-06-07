# Copyright (c) 2025 Thomas Dubois
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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






class AbstractTimerUtils:
    def __init__(self, timer_provider):
        self._timer_provider = timer_provider
        self._timer_ids = {}


    def _add_timer(self, timer_name, cb, duration, once=True):
        self._remove_timer(timer_name)
#        print("Adding timer "+timer_name + " with duration "+ str(duration))
        self._timer_ids[timer_name] = self._timer_provider().timeout_add(duration, exit_on_error, self._trigger_and_remove_timer, timer_name, cb, once)


    def _remove_timer(self, timer_name):
        if timer_name in self._timer_ids and self._timer_ids[timer_name] is not None:
#            print("Removing timer "+timer_name)
            self._timer_provider().source_remove(self._timer_ids[timer_name])
            self._timer_ids[timer_name] = None

    def _trigger_and_remove_timer(self, timer_name, cb, once):
        should_keep_trigger = cb()

        if once or not should_keep_trigger:
            self._timer_ids[timer_name] = None
            return False
        
        return should_keep_trigger
