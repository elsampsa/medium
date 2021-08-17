"""This is an additional example to my medium article about combining python multithreading- and processing:

https://medium.com/@sampsa.riikonen/doing-python-multiprocessing-the-right-way-a54c1880e300

That article is a pre-requisite for you to understand this code, so you *must* read it first.

You might also want to read:

- Python's select module tutorial
- Linux shmem documentation

Two examples are included here:

Example 1:

    - Handling interprocess communications properly from the main process with the subprocesses
    - Posix shared memory is used to pass a numpy array to the multiprocess and getting another one in return
    - With shmem you might need to clean the shmem every now and then, especially if you program crashes, with: "rm -f /dev/shm/*"
    
Example 2:

    - A thread that is handling the multiprocesses of Example 1
    - You will learn that the frontend/backend methodology applies to threads as well
    - Special care is taken to perform the fork first and only after that, spawn the thread
    - This example uses python's threading module, but it is straightforward to extend it to Qt's QThread
    - In your Qt program you would handle with this thread the slot/signal interactions with the python multiprocess
"""

import os, sys, time, signal, select, random
import numpy as np
from multiprocessing import Process, Pipe, shared_memory
import threading

# *** EXAMPLE 1 ***

class MyProcess(Process):

    def __init__(self, name = "nada"):
        super().__init__()
        self.name = name
        self.front_pipe, self.back_pipe = Pipe()
        # Create a model numpy array:
        a = np.array([1, 2, 3, 4, 5, 6])
        # Create shared memory in the frontend: note create=True
        self.shm_in = shared_memory.SharedMemory(name = self.name+"_in", create=True, size=a.nbytes)
        self.shm_out = shared_memory.SharedMemory(name = self.name+"_out", create=True, size=a.nbytes)
        # Create a NumPy arrays from the shared memory
        self.arr_in = np.ndarray(a.shape, dtype=a.dtype, buffer=self.shm_in.buf)
        self.arr_out = np.ndarray(a.shape, dtype=a.dtype, buffer=self.shm_out.buf)

    # BACKEND

    def run(self):
        #from SomeLibrary import Analyzer
        #self.analyzer = Analyzer()
        # ignore CTRL-C in this subprocess:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        # Create a model numpy array:
        a = np.array([1, 2, 3, 4, 5, 6])
        # Create shared memory in the backend: note create=False
        self.shm_in = shared_memory.SharedMemory(name = self.name+"_in", create=False, size=a.nbytes)
        self.shm_out = shared_memory.SharedMemory(name = self.name+"_out", create=False, size=a.nbytes)
        # Create a NumPy arrays from the shared memory
        self.arr_in = np.ndarray(a.shape, dtype=a.dtype, buffer=self.shm_in.buf)
        self.arr_out = np.ndarray(a.shape, dtype=a.dtype, buffer=self.shm_out.buf)
        self.active = True
        while self.active:
            self.active = self.listenFront__()
        print("bye from multiprocess!")

    def listenFront__(self):
        message = self.back_pipe.recv()
        if message == "stop":
            # quit using shmem in the backend
            self.shm_in.close()
            self.shm_out.close()
            return False
        elif message == "doCalculation":
            self.doCalculation__()
            return True
        else:
            print("listenFront__ : unknown message", message)
            return True

    def doCalculation__(self):
        print("backend:", self.name,"doing calculation with", self.arr_in)
        time.sleep(2) # simulate a heavy calculation
        self.arr_out[:] = random.randint(1,10)
        print("backend:", self.name,"calculations results:", self.arr_out)
        self.back_pipe.send("ready")

    # FRONTEND

    def getPipe(self):
        return self.front_pipe

    def doCalculation(self):
        print("frontend:", self.name,"will do calculation with", self.arr_in)
        self.front_pipe.send("doCalculation")
        
    def stop(self):
        self.front_pipe.send("stop")
        self.join()
        # quit using shmem in the frontend
        self.shm_in.close()
        self.shm_out.close()
        # release shmem definitely
        self.shm_in.unlink()
        self.shm_out.unlink()


# *** EXAMPLE 2 ***

class HandlerThread(threading.Thread):
    """A thread has a back- and frontend, exactly in the same way a multiprocess! :)

    However, for threads, all objects are seen / are the same for front- and backend, so their access needs to be protected with locks.

    This example is compatible with Qt's QThread for PyQt or PySide2, just change the mother class into QThread.  And remember to define your signals and slots properly.
    """
    def __init__(self):
        super().__init__()
        self.front_pipe, self.back_pipe = Pipe()
        self.processes_by_pipe = {} # key: a readable pipe, value: the corresponding process
        self.comlist = [] # list of tuples: (str, obj), representing the functions backend should perform
        self.comlist_lock = threading.Lock() # this is multithreading: we need to protect this list used both by front- and backend

    # BACKEND

    def run(self):
        """Threads functionality

        - listen to multiple intercommunication channels: pipes from the frontend and from the multiprocesses
        - new multiprocesses can be registered
        - Qt NOTE: define backend slots and send signals with their .emit() method
        """
        self.active = True
        while self.active:
            # Qt NOTE: feel free to send your custom signals with .emit from within this loop
            rlis = [pipe for pipe, process in self.processes_by_pipe.items()]
            rlis.append(self.back_pipe)
            # now rlis includes all pipes we need to listen: pipes of the processes & the intercom pipe of this thread
            r, w, e = select.select(rlis, [], [], 1) # one sec timeout
            if (len(r) < 1):
                print("thread backend: no messages from main thread but I'm still alive")
                continue
            for pipe in r: # run through all pipes that are ready for reading
                if (pipe == self.back_pipe): # this thread's intercom pipe
                    msg = pipe.recv()
                    print("thread backend: message from the main program", msg)
                    if msg == "com":
                        # thread is notified that it should take a look into self.comlist
                        with self.comlist_lock: # we're doing multithreading, so protect comlist access with a lock
                            comstr, obj = self.comlist.pop()
                            print("thread backend: comstr, obj", comstr, obj)
                            if comstr == "addProcess":
                                self.addProcess__(obj)
                            elif comstr == "someSlot":
                                self.someSlot__(obj)
                    elif msg == "stop":
                        self.active = False
                        break
                else: # must be multiprocesses intercom pipe
                    process = self.processes_by_pipe[pipe]
                    msg = pipe.recv()
                    print("thread backend: message from process", process)
                    if msg == "ready":
                        print("thread backend: got from process", process, "result", process.arr_out)
                        # Qt NOTE: nice place to create a copy of your numpy array and send it to the ether as a signal
                        process.arr_in[:] = random.randint(1,5) # put input values for calculation
                        process.doCalculation() # calculate again
        print("thread: bye!")
                

    def addProcess__(self, process: MyProcess):
        """Register a process & start a calculation
        """
        self.processes_by_pipe[process.getPipe()] = process
        process.arr_in[:] = random.randint(1,8) # put input values for calculation
        process.doCalculation() # calculate again


    def someSlot__(self, par):
        print("thread backend: someSlot", par)


    # FRONTEND

    def addProcess(self, process: MyProcess):
        """Tell thread to start listening to a multiprocess
        """
        with self.comlist_lock: # we're doing multithreading, so protect comlist access with a lock
            self.comlist.append((
                "addProcess", process
            ))
        self.front_pipe.send("com") # tell thread backend to check out comlist

    
    def someSlot(self, par):
        """Qt NOTE: If this was a QThread, you would connect your signals to a slot like this, however..

        ..remember that the actual functionality of the slot must happen at QThread's backend!  In this case, in the backend method "someSlot__"
        """
        with self.comlist_lock: # we're doing multithreading, so protect comlist access with a lock
            self.comlist.append((
                "someSlot", par
            ))
        self.front_pipe.send("com") # tell thread backend to check out comlist


    def stop(self):
        self.front_pipe.send("stop")
        self.join() # Qt NOTE: use self.wait() instead



def main1():
    """Example 1
    """
    p1 = MyProcess(name="test_process_1")
    p2 = MyProcess(name="test_process_2")
    p1.start()
    p2.start()
    p1_pipe = p1.getPipe()
    p2_pipe = p2.getPipe()
    # start calculating something
    p1.arr_in[:] = 1.
    p2.arr_in[:] = 2.
    p1.doCalculation()
    p2.doCalculation()
    while True:
        try:
            rlis = [p1_pipe, p2_pipe]
            r, w, e = select.select(rlis, [], [], 1) # one sec timeout
            if p1_pipe in r:
                msg = p1_pipe.recv()
                print("main process: message from process p1", msg)
                if msg == "ready":
                    print("main process: got from process p1,", p1.arr_out)
                    p1.arr_in[:] = random.randint(1,5) # put input values for calculation
                    p1.doCalculation() # calculate again
            elif p2_pipe in r:
                msg = p2_pipe.recv()
                print("main process: message from process p2", msg)
                if msg == "ready":
                    print("main process: got from process p2,", p2.arr_out)
                    p2.arr_in[:] = random.randint(1,8) # put input values for calculation
                    p2.doCalculation() # calculate again
            elif len(r) < 1:
                print("main process: no messages from subprocesses but I'm still alive")
        except KeyboardInterrupt:
            print("you pressed CTRL-C: I will exit")
            p1.stop()
            p2.stop()
            break


def main2():
    """Example 2
    """
    # create & start multiprocesses
    p1 = MyProcess(name="test_process_1")
    p2 = MyProcess(name="test_process_2")
    # fork - before starting any threads, of course
    print("starting processes")
    p1.start()
    p2.start()
    # create & start threads
    t = HandlerThread()
    print("starting thread")
    t.start()
    # thread is running!
    time.sleep(3)
    # issue the thread to listen to the multiprocesses
    t.addProcess(p1)
    t.addProcess(p2)
    time.sleep(1)
    t.someSlot(par="kokkelis")
    time.sleep(5)
    # stop thread
    print("stopping thread")
    t.stop()
    # stop multiprocesses
    p1.stop()
    p2.stop()


# choose one of the examples for running:
#main1()
main2()

