from time import time, sleep
from pytest import mark, fixture

from .emitter import Emitter
from .config import is_backend, get_backend, set_backend, Backend
from tools import Fn, Print, Open, Grep, Reverse, Iter

@fixture(scope="module", params=[Backend.MULTIPROCESSING, Backend.THREADING, Backend.DUMMY])
def emitter_backend(request):
    """Change the emitter library to use a threading backend for the test
    """
    original_backend = get_backend()
    set_backend(request.param)
    def fin():
        set_backend(original_backend)
    request.addfinalizer(fin)

@mark.usefixtures("emitter_backend")
class TestBasicEmitterTools:
    def test_fn_basic(self):
        assert Iter(range(10)).into(Fn(lambda x: x*x)).results() == [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

    def test_print(self):
        assert Iter(range(10)).into(Print()).results() == []

    def test_open(self):
        fname = "/tmp/test-open-" + str(time())
        with open(fname, 'w') as f:
            f.write("Line1\n")
            f.write("Line2\n")
            f.write("Line3\n")
        assert Open(fname).results() == ["Line1\n", "Line2\n", "Line3\n"]
        assert Iter([fname]).into(Open()).results() == ["Line1\n", "Line2\n", "Line3\n"]

    def test_grep(self):
        assert Iter(["dogs", "dog", "heydog", "other"]).into(Grep("dog$")).results() == ["dog", "heydog"]

    def test_reversed(self):
        assert Iter(range(4)).into(Reverse()).results() == [3, 2, 1, 0]

def sq(x):
    return x*x

def multiply_ten(x):
    return x*10

class SlowEmitter(Emitter):
    def setup(self, sleeptime=0.1):
        self.sleep = sleeptime
    def do(self, value):
        sleep(self.sleep)

@mark.usefixtures("emitter_backend")
class TestBasicEmitterPipelines:
    def test_two_sequential(self):
        pipe = Iter(range(10)).into(Fn(sq)).into(Fn(multiply_ten))
        assert pipe.results() == [0, 10, 40, 90, 160, 250, 360, 490, 640, 810]

    def test_three_sequential(self):
        pipe = Iter(range(10)).into(Fn(sq)).into(Fn(multiply_ten)).into(Fn(multiply_ten))
        assert pipe.results() == [0, 100, 400, 900, 1600, 2500, 3600, 4900, 6400, 8100]

    def test_multi(self):
        start = time()
        Iter(range(10)).into(SlowEmitter()).execute()
        finish = time() - start
        if is_backend(Backend.MULTIPROCESSING): assert 0.9 < finish < 1.1
        if is_backend(Backend.THREADING): assert 0.9 < finish < 1.1
        if is_backend(Backend.DUMMY): assert 0.9 < finish < 1.1

        start = time()
        Iter(range(10)).into(SlowEmitter(processes=2)).execute()
        finish = time() - start
        if is_backend(Backend.MULTIPROCESSING): assert 0.4 < finish < 1.0
        if is_backend(Backend.THREADING): assert 0.4 < finish < .7
        if is_backend(Backend.DUMMY): assert 0.9 < finish < 1.1

        start = time()
        Iter(range(10)).into(SlowEmitter(processes=4)).execute()
        finish = time() - start
        if is_backend(Backend.MULTIPROCESSING): assert 0.2 < finish < 0.6
        if is_backend(Backend.THREADING): assert 0.2 < finish < 0.5
        if is_backend(Backend.DUMMY): assert 0.9 < finish < 1.1

        start = time()
        Iter(range(10)).into(SlowEmitter(processes=10)).execute()
        finish = time() - start
        if is_backend(Backend.MULTIPROCESSING): assert finish < 0.4
        if is_backend(Backend.THREADING): assert finish < 0.4
        if is_backend(Backend.DUMMY): assert 0.9 < finish < 1.1

