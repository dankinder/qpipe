import re

from .emitter import Emitter
from subprocess import check_output

class Iter(Emitter):
    """Takes an iterable in its constructor and emits each item.

    Examples:
        Iter(range(10))
        Iter([1, 5, 10])
    """
    def setup(self, arg_iterable):
        for arg in arg_iterable:
            self.emit(arg)

class Fn(Emitter):
    """Takes a function and creates an emitter that calls it with each input and emits the results.

    Examples:
        def square(x):
            return x*x
        Fn(square)
        Fn(lambda x: x*x)
    """
    def setup(self, fn):
        self.fn = fn
    def do(self, arg):
        self.emit(self.fn(arg))

class Print(Emitter):
    """Prints each incoming element using python's native print function.
    """
    def do(self, arg):
        print(arg)

class Open(Emitter):
    """Emits lines from a file
    Can be used in two ways:
    - Construct with a filename: `Open("myfile.txt")`
    - Feed with files: `Iter(["myfile1.txt", "myfile2.txt"]).into(Open())`
    In either case will emit lines one by one from given files
    """
    def setup(self, filename=None):
        self.emitfile(filename)

    def do(self, filename):
        self.emitfile(filename)

    def emitfile(self, filename):
        if not filename:
            return
        with open(filename) as f:
            for line in f:
                self.emit(line)

class Exec(Emitter):
    """Executes a command and emits the output of the command as returned by subprocess.check_output

    Can take a command as constructor or multiple commands from an upstream emitter:
        Exec("uname -a")
        Iter(["echo 'hi there'", "hostname"]).into(Exec())
    """
    def setup(self, command=None):
        if command:
            self.emit(check_output(command))
    def do(self, command):
        self.emit(check_output(command))

class Grep(Emitter):
    """Given a regular expression string as an argument, receives elements and only emits the ones matching the regex.

    Example:
        Iter(["hello", "goodbye", "helloww"]).into(Grep("hello")) # Emits "hello" and "helloww"
    """
    def setup(self, grepstring):
        self.regex = re.compile(grepstring)
    def do(self, text):
        if self.regex.search(text):
            self.emit(text)

class Reverse(Emitter):
    """Receives elements until none are left, then emits them in reverse order.

    Example:
        Iter([1, 2, 3]).into(Reverse()) # Emits 3, 2, 1
    """
    def setup(self):
        self.data = []
    def do(self, value):
        self.data.append(value)
    def teardown(self):
        for val in reversed(self.data):
            self.emit(val)
