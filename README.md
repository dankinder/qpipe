# Emitter

Emitter is a syntatically clean and generic way of writing concurrent programs
using a flow model (like a graph of pipes). There are currently many ways of
writing [Flow Based Programs](https://wiki.python.org/moin/FlowBasedProgramming)
in python, but none seemed to have the simplicity, elegance, and
generlizeability that Emitter does (the closest probably being
[DAGPype](https://pypi.python.org/pypi/DAGPype) syntactically, and maybe
[pypes](https://bitbucket.org/diji/pypes/wiki/Home)).

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
processes that maybe be performing related tasks.

Implemented instead with the emitter library:

```python
from emitter import Emitter, Fn

def f(x):
    return x*x

if __name__ == '__main__':
    print(Iter([10, 20, 30]).into(Fn(f, processes=4)).results())
```

Here is the implementation of a more complicated pipeline using emitter, the
python equivalent of `tail -f myapp.log | grep error`:

```python
import re
from emitter import Emitter, Print

class Tail(Emitter):
    def setup(self, filename):
        for line in sh.tail("-f", filename, _iter=True):
            self.emit(line)

class Grep(Emitter):
    def setup(self, grepstring):
        self.regex = re.compile(grepstring)
    def do(self, text):
        if(self.regex.search(text)):
            self.emit(text)

if __name__ == '__main__':
    Tail("myapp.log").into(Grep("error")).into(Print()).execute()
```

## API

### Using Emitters

Constructing any emitter builds a pipeline. Use `into` to attach multiple
components together.

```python
Open("myfile.txt").into(Print())
```

Nothing happens until the pipeline is executed.

```python
# Starts printing lines from myfile.txt
Open("myfile.txt").into(Print()).execute()
```

Emitters like Open can start generating output using just constructor
arguments, but others (like Print) won't do anything unless values are piped
into them. Passing a list (or any iterable) to the provided Iter emitter works
for this.

```python
# Prints the list contents on separate lines
Iter(["hello world", 4, []]).into(Print()).execute()
```

Emitters can easily be paralellized by specifying a `processes` keyword
argument.

```python
# Runs the "complex math" in 4 processes
Iter(range(10000)).into(SomeComplexMath(processes=4)).into(Print()).execute()
```

Emitter pipelines can be started with the following calls:

`execute()`: start processing, block until completion, return nothing.
`start()`: start processing, do not block, return nothing.
`results()`: start processing (if not started already), block until completion, return results as a list.

See the [examples](examples) for a few more emitter program examples.

### Developing Emitters

To create your own emitter, subclass Emitter and override any of these methods:
- `setup`: called once per process at start. Constructor arguments passed to
your emitter that aren't used by the Emitter superclass will be passed along
to this method.
- `do`: called once for each input value.
- `teardown`: called once per process at the end.

Note that all of these are called on the processing thread. If you run an
Emitter with multiple processes then each one will call setup/teardown.
Instance variables are not shared.

Within your code, to send values to the next pipe (or results), call
`self.emit(value)`. `setup`, `do`, and `teardown` can all call `emit` 0 or
more times.

### Other relevant API calls

The backend emitter uses determines how tasks are parallelized. The current choices are:
- `Backend.MULTIPROCESSING`: the default backend. The emitters use
  [multiprocessing.Process](https://docs.python.org/2/library/multiprocessing.html#multiprocessing.Process)
  to execute tasks. If the `processes=X` keyword argument is used this causes
  that emitter to have X processes executing tasks at once.
- `Backend.THREADING`: similar to MULTIPROCESSING, but instead uses
  [threading.Thread](https://docs.python.org/2/library/threading.html#threading.Thread)
  objects. The amount of parallelism with this backend will be limited by
  python's Global Interpreter Lock (only a problem for CPU-intensive tasks),
  but does not have to serialize(pickle) data like the MULTIPROCESSING backend does.
- `Backend.DUMMY`: a simple backend for testing pipelines, not concurrent. It
  simply executes each stage of the pipeline and completes it before moving on
  to the next one.

These can be checked and set using the following functions. This setting is
currently global and should not be changed while an emitter pipeline is
executing.
- `set_backend(Backend.THREADING)`
- `get_backend()`
- `is_backend(Backend.MULTIPROCESSING)`

## Alpha warning

I have created this library because I have found myself wanting to write
concurrent python many times but *not* wanting to deal with the complexity.

This implementation does work, but isn't very robust. It doesn't have any fancy
features like multiple inputs and outputs (multiplexing), pipelines cannot be
modified during execution, it hasn't been carefully tested for long-running
cases like listening for messages on a queue or connections on a port, and
exceptions can easily cause the pipeline to never complete. I would love to see
others be inspired by the API and contribute or implement it more robustly than
I have. Though bear in mind: the lack of fancy features is also deliberate.
Emitter is intended to be a library optimized for human understanding. This
means keeping complexity down.

All this to say: this is alpha software and the API could easily change,
especially of the tools in [tools.py](tools.py).
