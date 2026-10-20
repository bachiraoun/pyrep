"""
Ten processes, each running several threads, fighting over the same repository. Every writer stamps its data with
its own identity so that torn, mixed, lost or stale data is detected, and the repository is audited from disk at the end.
"""
import os
import time
import pickle
import threading
import unittest
import importlib

from pyrep import Repository

from helpers import (SCALE, LOCK_TIMEOUT, TemporaryRepository, audit_repository, check_record, describe,
                     fight_expected_files, fight_for_files, make_record, run_in_processes)

PROCESS_COUNT = 10
THREAD_COUNT  = 4
STEPS         = 8 * SCALE


def fight_worker(path, processIndex, threadCount, steps, resultQueue):
    """
    Process body: runs several writer threads that fight over files. Even numbered
    processes share one Repository instance between their threads, odd numbered
    processes give each thread its own instance.

    :Parameters:
        #. path (str): The repository path.
        #. processIndex (int): Index of this process.
        #. threadCount (int): Number of writer threads.
        #. steps (int): Number of files created by each thread.
        #. resultQueue (multiprocessing.Queue): Receives the result dictionary.
    """
    failures  = []
    count     = 1 if processIndex % 2 == 0 else threadCount
    instances = [Repository(path, timeout=LOCK_TIMEOUT) for _ in range(count)]

    def session(threadIndex):
        repo = instances[threadIndex % count]
        failures.extend(fight_for_files(repo, f'p{processIndex}t{threadIndex}', steps))

    threads = [threading.Thread(target=session, args=(index,)) for index in range(threadCount)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # Closing stops a locker that all instances of this process share, so it must wait for every thread
    instances[0].close()
    resultQueue.put({'process': processIndex, 'failures': failures})


def structure_worker(path, processIndex, threadCount, steps, resultQueue):
    """
    Process body: threads create, rename, copy and remove files inside directories
    that every process also creates, and all replace one shared file.

    :Parameters:
        #. path (str): The repository path.
        #. processIndex (int): Index of this process.
        #. threadCount (int): Number of threads.
        #. steps (int): Number of file groups created by each thread.
        #. resultQueue (multiprocessing.Queue): Receives the result dictionary.
    """
    failures  = []
    instances = [Repository(path, timeout=LOCK_TIMEOUT) for _ in range(threadCount)]

    def session(threadIndex):
        writerId = f'p{processIndex}t{threadIndex}'
        repo     = instances[threadIndex]
        for step in range(steps):
            directory = f'common/d{step % 5}'
            base      = f'{directory}/{writerId}_{step}'
            for label, outcome in (('add_directory', repo.add_directory(directory, raiseError=False)),
                                   ('dump', repo.dump_file(make_record(writerId, step), base, raiseError=False)),
                                   ('rename', repo.rename_file(base, base + '_moved', raiseError=False)),
                                   ('copy', repo.copy_file(base + '_moved', base + '_copy', raiseError=False)),
                                   ('remove', repo.remove_file(base + '_copy', raiseError=False)),
                                   ('replace', repo.dump_file(make_record(writerId, step), 'common/replaced', replace=True, raiseError=False))):
                if not outcome[0]:
                    failures.append(f'{label} {base} failed: {outcome[1]}')
            moved = repo.pull_file(base + '_moved')
            if moved != make_record(writerId, step):
                failures.append(f'moved file {base} changed content')
            isValid, reason = check_record(repo.pull_file('common/replaced'))
            if not isValid:
                failures.append(f'replaced file is torn: {reason}')

    threads = [threading.Thread(target=session, args=(index,)) for index in range(threadCount)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # Closing stops a locker that all instances of this process share, so it must wait for every thread
    instances[0].close()
    resultQueue.put({'process': processIndex, 'failures': failures})


def race_worker(path, processIndex, startAt, resultQueue):
    """
    Process body: waits for a common start time and then dumps the same new name as everybody else.

    :Parameters:
        #. path (str): The repository path.
        #. processIndex (int): Index of this process.
        #. startAt (float): Epoch time at which every process fires.
        #. resultQueue (multiprocessing.Queue): Receives the result dictionary.
    """
    repo = Repository(path, timeout=LOCK_TIMEOUT)
    while time.time() < startAt:
        time.sleep(0.001)
    succeeded, message = repo.dump_file(make_record(f'p{processIndex}', 0), 'race/name', raiseError=False)
    repo.close()
    resultQueue.put({'process': processIndex, 'succeeded': succeeded, 'message': message})


def counter_worker(path, processIndex, finalSequence, timeoutSeconds, resultQueue):
    """
    Process body: process 0 writes the growing counter record, every other process
    reads it continuously and checks that it is intact and never goes backwards.

    :Parameters:
        #. path (str): The repository path.
        #. processIndex (int): Index of this process, 0 is the writer.
        #. finalSequence (int): Last sequence the writer produces.
        #. timeoutSeconds (number): How long readers wait to see the final sequence.
        #. resultQueue (multiprocessing.Queue): Receives the result dictionary.
    """
    repo     = Repository(path, timeout=LOCK_TIMEOUT)
    failures = []
    reads    = 0
    if processIndex == 0:
        for sequence in range(1, finalSequence + 1):
            succeeded, message = repo.update_file(make_record('counter', sequence), 'counter', raiseError=False)
            if not succeeded:
                failures.append(f'counter update {sequence} failed: {message}')
    else:
        last     = -1
        deadline = time.time() + timeoutSeconds
        while last < finalSequence and time.time() < deadline:
            record = repo.pull_file('counter')
            reads += 1
            isValid, reason = check_record(record)
            if not isValid:
                failures.append(f'counter record torn: {reason}')
                break
            if record['sequence'] < last:
                failures.append(f"counter went back from {last} to {record['sequence']}")
            last = max(last, record['sequence'])
        if last < finalSequence:
            failures.append(f'reader never saw the final sequence, last seen {last}')
    repo.close()
    resultQueue.put({'process': processIndex, 'failures': failures, 'reads': reads})


def atomic_contender(path, identity, isWriter, rounds, seconds, resultQueue):
    """
    Process body: either writes a large value stamped with its identity to a contended file, straight through
    the atomic writer and without any lock, which is the worst case locks can fail into, or reads that file
    over and over and counts the reads that are not one complete value of one writer.

    :Parameters:
        #. path (str): The contended file.
        #. identity (int): Identity of this process, 1 to 255 for writers.
        #. isWriter (bool): Whether this process writes or reads.
        #. rounds (int): Number of writes of a writer.
        #. seconds (number): How long a reader keeps reading.
        #. resultQueue (multiprocessing.Queue): Receives the result dictionary.
    """
    errors = corrupt = reads = 0
    if isWriter:
        module = importlib.import_module('pyrep.Repository')
        for _ in range(rounds):
            try:
                module.write_pickle_atomically(path, {'id': identity, 'blob': bytes([identity]) * 3000000}, 2)
            except Exception:
                errors += 1
    else:
        stopAt = time.time() + seconds
        while time.time() < stopAt:
            try:
                with open(path, 'rb') as fd:
                    value = pickle.load(fd)
            except FileNotFoundError:
                continue
            except Exception:
                corrupt += 1
                reads   += 1
                continue
            reads += 1
            if value['blob'] != bytes([value['id']]) * 3000000:
                corrupt += 1
    resultQueue.put({'process': identity, 'isWriter': isWriter, 'errors': errors, 'corrupt': corrupt, 'reads': reads})


class TestProcessesFighting(unittest.TestCase):
    """
    The fights, audited from disk afterwards.
    """

    def setUp(self):
        self.temporary = TemporaryRepository()
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo

    def collect_failures(self, results):
        """
        Flattens the failures reported by all processes.
        """
        return [failure for result in results for failure in result['failures']]

    def test_ten_processes_fight_over_files_and_info(self):
        """Own files, own info and one hot shared file stay exact under 10 processes x 4 threads."""
        self.repo.dump_file(make_record('seed', 0, size=30000), 'shared/hot')
        results  = run_in_processes(fight_worker, [(self.temporary.path, index, THREAD_COUNT, STEPS) for index in range(PROCESS_COUNT)])
        failures = self.collect_failures(results)
        self.assertEqual(failures, [], describe(failures))
        writerIds = [f'p{process}t{thread}' for process in range(PROCESS_COUNT) for thread in range(THREAD_COUNT)]
        expected  = fight_expected_files(writerIds, STEPS)
        problems  = audit_repository(self.temporary.path, expectedFiles=expected)
        self.assertEqual(problems, {}, describe(problems))

    def test_ten_processes_create_rename_copy_remove(self):
        """Structural changes in shared directories lose nothing and leave nothing behind."""
        self.repo.dump_file(make_record('seed', 0), 'common/replaced')
        results  = run_in_processes(structure_worker, [(self.temporary.path, index, THREAD_COUNT, STEPS) for index in range(PROCESS_COUNT)])
        failures = self.collect_failures(results)
        self.assertEqual(failures, [], describe(failures))
        expected = set(['common/replaced'])
        for process in range(PROCESS_COUNT):
            for thread in range(THREAD_COUNT):
                for step in range(STEPS):
                    expected.add(f'common/d{step % 5}/p{process}t{thread}_{step}_moved')
        problems = audit_repository(self.temporary.path, expectedFiles=expected)
        self.assertEqual(problems, {}, describe(problems))

    def test_ten_processes_race_for_one_name(self):
        """When 10 processes fire at the same instant, exactly one dump wins and its data is stored."""
        startAt = time.time() + 6
        results = run_in_processes(race_worker, [(self.temporary.path, index, startAt) for index in range(PROCESS_COUNT)])
        winners = [result['process'] for result in results if result['succeeded']]
        self.assertEqual(len(winners), 1, describe(results))
        # A fresh instance is needed because this one never saw what the other processes tracked
        fresh = Repository(self.temporary.path, timeout=LOCK_TIMEOUT)
        stored = fresh.pull_file('race/name')
        self.assertTrue(check_record(stored)[0])
        self.assertEqual(stored['writer'], f'p{winners[0]}')
        self.assertEqual(audit_repository(self.temporary.path), {})

    def test_unlocked_writers_never_publish_a_torn_file(self):
        """Even when nothing keeps writers apart, the file a reader opens is always one complete value of one writer."""
        path = os.path.join(self.temporary.root, 'contended')
        with open(path, 'wb') as fd:
            pickle.dump({'id': 0, 'blob': bytes([0]) * 3000000}, fd)
        arguments = [(path, index, True, 15, 0) for index in range(1, 5)] + [(path, 100 + index, False, 0, 6) for index in range(2)]
        results   = run_in_processes(atomic_contender, arguments)
        readers   = [result for result in results if not result['isWriter']]
        self.assertEqual(sum(result['errors'] for result in results), 0)
        self.assertEqual(sum(result['corrupt'] for result in readers), 0)
        self.assertGreater(sum(result['reads'] for result in readers), 0)
        with open(path, 'rb') as fd:
            final = pickle.load(fd)
        self.assertEqual(final['blob'], bytes([final['id']]) * 3000000)
        leftovers = [name for name in os.listdir(self.temporary.root) if name.startswith('.pyreptmp_')]
        self.assertEqual(leftovers, [])

    def test_readers_never_see_torn_or_older_data(self):
        """One writer process and nine reader processes: every read is intact and time never goes backwards."""
        finalSequence = 60 * SCALE
        self.repo.dump_file(make_record('counter', 0), 'counter')
        results  = run_in_processes(counter_worker, [(self.temporary.path, index, finalSequence, 120) for index in range(PROCESS_COUNT)])
        failures = self.collect_failures(results)
        self.assertEqual(failures, [], describe(failures))
        self.assertGreater(sum(result['reads'] for result in results), 0)
        fresh = Repository(self.temporary.path, timeout=LOCK_TIMEOUT)
        self.assertEqual(fresh.pull_file('counter')['sequence'], finalSequence)


if __name__ == '__main__':
    unittest.main()
