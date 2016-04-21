from time import sleep
from Queue import Queue, Empty
import multiprocessing
import threading

from .config import is_backend, Backend

class Emitter:
    """
    Subclass this class with your own to create pluggable Emitter component.

    Implement Emitter behavior by overriding any of the following methods:

    :setup: called with any arguments you pass to the Emitter's constructor
    :do: called once for each value from the upstream Emitter
    :teardown: called once when this Emitter has finished receiving values

    These methods do nothing unless overridden.
    """

    ## Methods that run on emitter thread(s)
    #

    def setup(self, *largs, **dargs):
        """Overridden to initialize the component (emit can be used)
        """
        pass

    def do(self, *largs, **dargs):
        """Should be overridden by user class
        """
        pass

    def teardown(self, *largs, **dargs):
        """Overridden to execute code before the node finishes (emit can be used)
        """
        pass

    def emit(self, value):
        """Send a value on to the next emitter

        If there are multiple emitters, distribute round-robin
        """
        if len(self._output_queues) > 0:
            output_queue, other_emitter = self._output_queues[self._next_output_queue_index]
            output_queue.put(value)

            self._next_output_queue_index += 1
            if self._next_output_queue_index >= len(self._output_queues):
                self._next_output_queue_index = 0

        if self._results != None:
            # This is safe because _results is a shared list, created by a manager
            self._results.append(value)

    ## Methods that run on the constructing/main thread
    #

    def __init__(self, *largs, **dargs):
        # The args to pass through; Emitter args removed during init
        self._passthrough_list_args = largs
        self._passthrough_dict_args = dargs

        self._processes = []
        if not 'processes' in dargs:
            dargs['processes'] = 1

        for i in range(dargs['processes']):
            if is_backend(Backend.THREADING):
                emitterclass = _EmitterThread
            elif is_backend(Backend.MULTIPROCESSING):
                emitterclass = _EmitterProcess
            elif is_backend(Backend.DUMMY):
                emitterclass = _EmitterDummy

            procname = "{0}{1}".format(self.__class__.__name__, i)
            self._processes.append(emitterclass(name=procname, emitter_instance=self))

        del self._passthrough_dict_args['processes']

        self._started_operating = False
        self._results = None
        self._output_queues = [] # elements: (Queue, other Emitter)
        self._next_output_queue_index = 0 # For round-robin queueing

        self._input_queues = [] # elements: (Queue, other Emitter or None if iterable used)

    def infrom(self, upstream):
        """Connect this pipe to :upstream: so that the output of :upstream: is
        this pipe's input. Returns :self: (the downstream pipe), for chaining.
        """
        if self._started_operating:
            raise Exception("You cannot change an emitter flow once it is running")

        if is_backend(Backend.MULTIPROCESSING):
            new_queue = multiprocessing.Queue()
        else:
            new_queue = Queue()

        self._input_queues.append((new_queue, upstream))
        upstream._output_queues.append((new_queue, self))
        return upstream

    def into(self, input_target):
        """Connect this pipe to :upstream: so that the output of :self: is the
        input of :input_target:. Returns :input_target: (the downstream pipe),
        for chaining.
        """
        input_target.infrom(self)
        return input_target

    def execute(self):
        """Start the flow, block until completion, and do not return any results.
        """
        self.start()

        #TODO: join all processes; the current system only works cleanly with one output emitter
        if not is_backend(Backend.DUMMY):
            for p in self._result_emitter()._processes:
                p.join()

    def start(self):
        """Start the flow, do not block until complection, and do not return any results.
        """
        if self._started_operating:
            raise Exception("You cannot start an emitter flow that has already been run")
        self._start_operating()

    def results(self):
        """Start the flow, block until completion, and return the results.
        """
        if self._started_operating:
            raise Exception("You cannot start an emitter flow that has already been run")
        result_emitter = self._result_emitter()

        if is_backend(Backend.MULTIPROCESSING):
            result_emitter._results = multiprocessing.Manager().list()
        else:
            result_emitter._results = []

        self.execute()

        if is_backend(Backend.MULTIPROCESSING):
            return list(result_emitter._results)
        else:
            return result_emitter._results

    def _start_operating(self):
        if self._started_operating:
            return
        self._started_operating = True

        # Here, for the dummy emitter, we assume the graph to be a DAG
        for _, input_emitter in self._input_queues:
            if input_emitter:
                input_emitter._start_operating()

        for p in self._processes:
            p.start()

        for _, output_emitter in self._output_queues:
            if output_emitter:
                output_emitter._start_operating()

    def _result_emitter(self):
        if len(self._output_queues) == 0:
            return self
        return self._output_queues[0][1]._result_emitter()

    def _output_complete(self):
        for p in self._processes:
            if not p._output_complete_event.is_set():
                return False
        return True

class _EmitterProcess(multiprocessing.Process):

    def __init__(self, name, emitter_instance):
        multiprocessing.Process.__init__(self, name=name)
        self.emitter = emitter_instance
        self._output_complete_event = multiprocessing.Event()

    def run(self):
        self.emitter.setup(*self.emitter._passthrough_list_args,
                           **self.emitter._passthrough_dict_args)

        while True:
            # If all inputs claim to be done, make one more pass for data,
            # then finish up
            all_inputs_complete = True
            for input_queue, other_emitter in self.emitter._input_queues:
                if other_emitter and not other_emitter._output_complete():
                    all_inputs_complete = False
                    break

            # Consume from each queue
            for input_queue, other_emitter in self.emitter._input_queues:
                try:
                    while True:
                        self.emitter.do(input_queue.get_nowait())
                except Empty:
                    pass

            if all_inputs_complete:
                break
            sleep(0.01)

        self.emitter.teardown()

        # Make sure output queues are flushed out
        for output_queue, other_emitter in self.emitter._output_queues:
            output_queue.close()
        for output_queue, other_emitter in self.emitter._output_queues:
            output_queue.join_thread()
        self._output_complete_event.set()

class _EmitterThread(threading.Thread):

    def __init__(self, name, emitter_instance):
        threading.Thread.__init__(self, name=name)
        self.emitter = emitter_instance
        self._output_complete_event = threading.Event()

    def run(self):
        self.emitter.setup(*self.emitter._passthrough_list_args,
                           **self.emitter._passthrough_dict_args)

        while True:
            # If all inputs claim to be done, make one more pass for data,
            # then finish up
            all_inputs_complete = True
            for input_queue, other_emitter in self.emitter._input_queues:
                if other_emitter and not other_emitter._output_complete():
                    all_inputs_complete = False
                    break

            # Consume from each queue
            for input_queue, other_emitter in self.emitter._input_queues:
                try:
                    while True:
                        self.emitter.do(input_queue.get_nowait())
                except Empty:
                    pass

            if all_inputs_complete:
                break
            sleep(0.01)

        self.emitter.teardown()
        self._output_complete_event.set()

class _EmitterDummy:
    """Emitter implementation that fakes a real process.

    When start() is called, it simply reads from all input queues, does all
    execution, then closes out. Used for testing. Only works if the pipeline
    is directed and acyclic.
    """

    def __init__(self, name, emitter_instance):
        self.emitter = emitter_instance
        self._output_complete_event = threading.Event()

    def start(self):
        self.emitter.setup(*self.emitter._passthrough_list_args,
                           **self.emitter._passthrough_dict_args)

        while True:
            # If all inputs claim to be done, make one more pass for data,
            # then finish up
            all_inputs_complete = True
            for input_queue, other_emitter in self.emitter._input_queues:
                if other_emitter and not other_emitter._output_complete():
                    all_inputs_complete = False
                    break

            # Consume from each queue
            for input_queue, other_emitter in self.emitter._input_queues:
                try:
                    while True:
                        self.emitter.do(input_queue.get_nowait())
                except Empty:
                    pass

            if all_inputs_complete:
                break
            sleep(0.01)

        self.emitter.teardown()
        self._output_complete_event.set()

