# QPipe

QPipe ("Quick-Pipe", or "Queue-Pipe") is a syntatically clean and generic way
of writing concurrent programs using a flow model (like a graph of pipes).
There are currently many ways of writing [Flow Based
Programs](https://wiki.python.org/moin/FlowBasedProgramming) in python, but
none seemed to have the simplicity, elegance, and generlizeability that QPipe
does (the closest probably being
[pipedream](https://github.com/tgecho/pipedream/) and maybe
[pypes](https://bitbucket.org/diji/pypes/wiki/Home)).

```bash
sudo pip install qpipe
```

## Overview

One of the simplest ways to parallelize in python is the Pool class:

```python
from multiprocessing import Pool

def f(x):
    return x*x

if __name__ == '__main__':
    p = Pool(5)
    print(p.map(f, [1, 2, 3]))
```

This is simple but inflexible. It becomes orders of magnitude more complicated
to stream data while processing or inter-communicate with other distinct
processes that may be performing related tasks.

Implemented instead with the qpipe library:

```python
from qpipe import Pipe, Fn

def f(x):
    return x*x

if __name__ == '__main__':
    print(Iter([10, 20, 30]).into(Fn(f, processes=4)).results())
```

Here is the implementation of a more complicated pipeline using qpipe, the
python equivalent of `tail -f myapp.log | grep error`:

```python
import re
from qpipe import Pipe, Print

class Tail(Pipe):
    def setup(self, filename):
        for line in sh.tail("-f", filename, _iter=True):
            self.emit(line)

class Grep(Pipe):
    def setup(self, grepstring):
        self.regex = re.compile(grepstring)
    def do(self, text):
        if(self.regex.search(text)):
            self.emit(text)

if __name__ == '__main__':
    Tail("myapp.log").into(Grep("error")).into(Print()).execute()
```

## API

### Using Pipes

Constructing any qpipe builds a pipeline. Use `into` to attach multiple
components together.

```python
Open("myfile.txt").into(Print())
```

Nothing happens until the pipeline is executed.

```python
# Starts printing lines from myfile.txt
Open("myfile.txt").into(Print()).execute()
```

Pipes like Open can start generating output using just constructor
arguments, but others (like Print) won't do anything unless values are piped
into them. Passing a list (or any iterable) to the provided Iter qpipe works
for this.

```python
# Prints the list contents on separate lines
Iter(["hello world", 4, []]).into(Print()).execute()
```

Pipes can easily be parallelized by specifying a `processes` keyword
argument.

```python
# Runs the "complex math" in 4 processes
Iter(range(10000)).into(SomeComplexMath(processes=4)).into(Print()).execute()
```

Pipelines can be started with the following calls:

- `execute()`: start processing, block until completion, return nothing.
- `start()`: start processing, do not block, return nothing.
- `results()`: start processing (if not started already), block until completion, return results as a list.

See the [examples](examples) for a few more qpipe program examples.

### Developing Custom Pipes

To create your own qpipe, subclass Pipe and override any of these methods:
- `setup`: called once per process at start. Constructor arguments passed to
your qpipe that aren't used by the Pipe superclass will be passed along
to this method.
- `do`: called once for each input value.
- `teardown`: called once per process at the end.

Note that all of these are called on the processing thread. If you run a
Pipe with multiple processes then each one will call setup/teardown.
Instance variables are not shared.

Within your code, to send values to the next pipe (or results), call
`self.emit(value)`. `setup`, `do`, and `teardown` can all call `emit` 0 or
more times.

### Other relevant API calls

The backend qpipe uses determines how tasks are parallelized. The current choices are:
- `Backend.MULTIPROCESSING`: the default backend. The pipes use
  [multiprocessing.Process](https://docs.python.org/2/library/multiprocessing.html#multiprocessing.Process)
  to execute tasks. If the `processes=X` keyword argument is used this causes
  that pipe to have X processes executing tasks at once.
- `Backend.THREADING`: similar to MULTIPROCESSING, but instead uses
  [threading.Thread](https://docs.python.org/2/library/threading.html#threading.Thread)
  objects. The amount of parallelism with this backend will be limited by
  python's Global Interpreter Lock (only a problem for CPU-intensive tasks),
  but does not have to serialize(pickle) data like the MULTIPROCESSING backend does.
- `Backend.DUMMY`: a simple backend for testing pipelines, not concurrent. It
  simply executes each stage of the pipeline and completes it before moving on
  to the next one.

These can be checked and set using the following functions. This setting is
currently global and should not be changed while pipeline is executing.
- `set_backend(Backend.THREADING)`
- `get_backend()`
- `is_backend(Backend.MULTIPROCESSING)`

## A word of caution

I have created this library because I have found myself wanting to write
concurrent python many times but *not* wanting to deal with the complexity.

This implementation does work, but isn't very robust. It doesn't have any fancy
features like multiple inputs and outputs (multiplexing), pipelines cannot be
modified during execution, it hasn't been carefully tested for long-running
cases like listening for messages on a queue or connections on a port, and
exceptions can easily cause the pipeline to never complete. I would love to see
others be inspired by the API and contribute or implement it more robustly than
I have. Though bear in mind: the lack of fancy features is also deliberate.
QPipe is intended to be a library optimized for human understanding. This
means keeping complexity down.

All this to say: this software should be considered in alpha and the API could
easily change, especially of the tools in [tools.py](qpipe/tools.py).
