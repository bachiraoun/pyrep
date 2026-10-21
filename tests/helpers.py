"""
Shared helpers of the pyrep test suite: temporary repositories, self-verifying records, process runners and integrity audits.
"""
import os
import time
import json
import queue
import shutil
import pickle
import hashlib
import tempfile
import unittest
import threading
import traceback
import collections
import multiprocessing

from pyrep import Repository

IS_QUICK_RUN = os.environ.get('PYREP_TEST_QUICK', '0') == '1'
SCALE        = max(1, int(os.environ.get('PYREP_TEST_SCALE', '1')))
LOCK_TIMEOUT = 60
HOT_SIZE     = 30000


def slow(func):
    """
    Marks a test as slow so that run_tests.py --quick skips it.

    :Parameters:
        #. func (callable): The test method to mark.

    :Returns:
        #. func (callable): The method, skipped on quick runs.
    """
    return unittest.skipIf(IS_QUICK_RUN, 'slow test, skipped by --quick')(func)


def known_bug(summary):
    """
    Marks a test as a confirmed bug that is not fixed yet. The test is reported
    as an expected failure, and as an unexpected success once the bug is fixed.

    :Parameters:
        #. summary (str): One sentence describing the bug.

    :Returns:
        #. decorator (callable): The decorator to apply to the test method.
    """
    def decorator(func):
        func.knownBug = summary
        return unittest.expectedFailure(func)
    return decorator


def record_checksum(body):
    """
    Computes the checksum that protects a record against torn or mixed writes.

    :Parameters:
        #. body (dict): The record with its 'writer', 'sequence' and 'payload' keys.

    :Returns:
        #. checksum (str): Hexadecimal SHA-256 digest of the record content.
    """
    content = {key: body[key] for key in ('writer', 'sequence', 'payload')}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode('utf-8')).hexdigest()


def make_record(writerId, sequence, size=300):
    """
    Builds a self-verifying record that carries the identity of its writer.

    :Parameters:
        #. writerId (str): Identity of the process and thread writing the record.
        #. sequence (int): Position of this write in the writer's own history.
        #. size (int): Number of payload items. Bigger records make torn writes likelier.

    :Returns:
        #. record (dict): The record with a checksum over its content.
    """
    body = {'writer': writerId, 'sequence': sequence, 'payload': [f'{writerId}:{sequence}:{index}' for index in range(size)]}
    body['checksum'] = record_checksum(body)
    return body


def check_record(record):
    """
    Verifies that a record was written completely by a single writer.

    :Parameters:
        #. record (object): The value read back from the repository.

    :Returns:
        #. isValid (bool): Whether the record is intact.
        #. reason (str): Why the record is invalid, empty when valid.
    """
    if not isinstance(record, dict) or set(record) != {'writer', 'sequence', 'payload', 'checksum'}:
        return False, f'unexpected structure {str(record)[:80]}'
    if record['checksum'] != record_checksum(record):
        return False, 'checksum mismatch'
    if any(item != f"{record['writer']}:{record['sequence']}:{index}" for index, item in enumerate(record['payload'])):
        return False, 'payload mixes several writers'
    return True, ''


class TemporaryRepository:
    """
    Context manager that creates a repository in a temporary directory and
    removes everything on exit.

    :Parameters:
        #. timeout (number): Lock timeout given to the repository instance.
        #. password (None, str): Locker password given to the repository instance.

    .. code-block:: python

        ## the repository only exists inside the with block
        with TemporaryRepository() as temporary:
            temporary.repo.dump_file('value', 'name')
    """

    def __init__(self, timeout=LOCK_TIMEOUT, password=None):
        self.timeout  = timeout
        self.password = password
        self.root     = None
        self.path     = None
        self.repo     = None

    def __enter__(self):
        self.root = tempfile.mkdtemp(prefix='pyrep_test_')
        self.repo = Repository(timeout=self.timeout, password=self.password)
        self.repo.create_repository(os.path.join(self.root, 'repo'))
        self.path = self.repo.path
        return self

    def __exit__(self, excType, excValue, excTraceback):
        self.repo.close()
        shutil.rmtree(self.root, ignore_errors=True)
        return False


def run_in_threads(target, argsList, timeoutSeconds=300):
    """
    Runs the target in one thread per arguments tuple and collects crashes.

    :Parameters:
        #. target (callable): Function run by every thread.
        #. argsList (list): One arguments tuple per thread.
        #. timeoutSeconds (number): Maximum time to wait for all threads.

    :Returns:
        #. crashes (list): Traceback text of every thread that raised.
    """
    crashes = []

    def guarded(args):
        try:
            target(*args)
        except Exception:
            crashes.append(traceback.format_exc()[-600:])

    threads = [threading.Thread(target=guarded, args=(args,)) for args in argsList]
    for thread in threads:
        thread.start()
    deadline = time.time() + timeoutSeconds
    for thread in threads:
        thread.join(max(0.1, deadline - time.time()))
    stuck = [thread for thread in threads if thread.is_alive()]
    if len(stuck):
        raise AssertionError(f'{len(stuck)} threads did not finish in {timeoutSeconds} seconds')
    return crashes


def run_in_processes(target, argsList, timeoutSeconds=300):
    """
    Runs the target in one fresh process per arguments tuple. Every process
    receives a result queue as its last argument and must put one result in it.

    :Parameters:
        #. target (callable): Module level function run by every process.
        #. argsList (list): One arguments tuple per process.
        #. timeoutSeconds (number): Maximum time to wait for all results.

    :Returns:
        #. results (list): One result per process, in completion order.
    """
    context     = multiprocessing.get_context('spawn')
    resultQueue = context.Queue()
    processes   = [context.Process(target=target, args=tuple(args) + (resultQueue,)) for args in argsList]
    for process in processes:
        process.start()
    results  = []
    deadline = time.time() + timeoutSeconds
    while len(results) < len(processes) and time.time() < deadline:
        try:
            results.append(resultQueue.get(timeout=1))
        except queue.Empty:
            # Stop waiting once every process is gone, because a crashed process never reports
            if not any(process.is_alive() for process in processes):
                break
    for process in processes:
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
    if len(results) < len(processes):
        raise AssertionError(f'only {len(results)} of {len(processes)} processes reported a result')
    return results


def audit_repository(path, expectedFiles=None):
    """
    Opens the repository from disk in a fresh instance and lists every
    inconsistency between the tracked list, the files and their info files.

    :Parameters:
        #. path (str): The repository path.
        #. expectedFiles (None, set): Exact set of relative file paths that must be tracked.

    :Returns:
        #. problems (dict): Problem name to the list of offending paths. Empty when consistent.
    """
    repo = Repository(path, timeout=LOCK_TIMEOUT)
    try:
        tracked  = list(repo.walk_files_path(recursive=True))
        dirList  = list(repo.walk_directories_path(recursive=True))
        problems = collections.defaultdict(list)
        problems['duplicate-file-entries'] = sorted(name for name, count in collections.Counter(tracked).items() if count > 1)
        problems['duplicate-directory-entries'] = sorted(name for name, count in collections.Counter(dirList).items() if count > 1)
        onDisk = set()
        for root, dirNames, fileNames in os.walk(path):
            for fileName in fileNames:
                relative = os.path.relpath(os.path.join(root, fileName), path)
                if fileName.endswith('_pyrepfilelock') or fileName == '.pyrepdirlock':
                    problems['stale-lock-files'].append(relative)
                elif fileName.endswith('_pyrepjournal') and not fileName.startswith('.pyreptmp_'):
                    problems['pending-commit-journals'].append(relative)
                elif fileName == '.pyrepjournal':
                    problems['pending-repository-journal'].append(relative)
                elif not fileName.startswith('.'):
                    onDisk.add(relative)
        for relative in sorted(set(tracked)):
            isRepoFile, fileOnDisk, infoOnDisk, classOnDisk = repo.is_repository_file(relative)
            if not fileOnDisk:
                problems['tracked-but-missing-on-disk'].append(relative)
                continue
            if not infoOnDisk or not classOnDisk:
                problems['tracked-without-info'].append(relative)
                continue
            try:
                repo.pull_file(relative)
            except Exception:
                problems['tracked-unreadable'].append(relative)
        problems['on-disk-but-untracked'] = sorted(onDisk - set(tracked))
        if expectedFiles is not None:
            problems['missing-expected'] = sorted(set(expectedFiles) - set(tracked))
            problems['unexpected-tracked'] = sorted(set(tracked) - set(expectedFiles))
        return {name: items for name, items in problems.items() if len(items)}
    finally:
        repo.close()


def read_index(path):
    """
    Reads the repository index file straight from disk, without the repair that
    loading a Repository does, so it shows exactly what was saved.

    :Parameters:
        #. path (str): The repository path.

    :Returns:
        #. tracked (set): Relative paths of the files the saved index lists.
    """
    with open(os.path.join(path, '.pyreprepo'), 'rb') as fd:
        index = pickle.load(fd)
    tracked = set()

    def walk(prefix, entries):
        for entry in entries:
            if isinstance(entry, dict):
                for name, children in entry.items():
                    walk(os.path.join(prefix, name), children)
            else:
                tracked.add(os.path.join(prefix, entry))

    walk('', index['walk_repo'])
    return tracked


def describe(items, limit=6):
    """
    Formats a list or a dict for assertion messages without flooding the output.

    :Parameters:
        #. items (list, dict): The things to describe.
        #. limit (int): Maximum number of entries shown.

    :Returns:
        #. text (str): Short description with the total count.
    """
    if isinstance(items, dict):
        return str({name: (len(values), values[:3]) for name, values in items.items()})
    return f'{len(items)} items, first: {items[:limit]}'


def fight_for_files(repo, writerId, steps, sharedName='shared/hot'):
    """
    Plays one writer's session. The writer dumps, reads back and updates its own
    files, each carrying info that only this writer can have produced, and fights
    with every other writer over one shared file that must never be seen torn.

    :Parameters:
        #. repo (pyrep.Repository): The repository instance used by this writer.
        #. writerId (str): Identity of the writer, unique across processes and threads.
        #. steps (int): Number of files this writer creates.
        #. sharedName (str): Relative path of the shared file, it must already exist.

    :Returns:
        #. failures (list): Description of every violated expectation, empty when all held.
    """
    failures     = []
    lastSequence = {}
    for step in range(steps):
        relative    = f'own/{writerId}/f{step}'
        description = f'owner={writerId} step={step}'
        succeeded, message = repo.dump_file(make_record(writerId, step), relative, description=description, raiseError=False)
        if not succeeded:
            failures.append(f'dump {relative} failed: {message}')
            continue
        # Nobody else touches this info file, so reading it without a lock is safe here
        info, message = repo.get_file_info(relative)
        if info is None or info['description'] != description:
            failures.append(f'info of {relative} is wrong: {info} {message}')
        if repo.pull_file(relative) != make_record(writerId, step):
            failures.append(f'{relative} read back different from what was dumped')
        updated, message = repo.update_file(make_record(writerId, step + 1000), relative,
                                            description=description + ' updated', raiseError=False)
        if not updated:
            failures.append(f'update {relative} failed: {message}')
        elif repo.pull_file(relative) != make_record(writerId, step + 1000):
            failures.append(f'{relative} read back different from what was updated')
        updated, message = repo.update_file(make_record(writerId, step, size=HOT_SIZE), sharedName, raiseError=False)
        if not updated:
            failures.append(f'shared update failed: {message}')
        try:
            seen = repo.pull_file(sharedName)
        except Exception as err:
            failures.append(f'shared pull failed: {str(err)[:150]}')
            continue
        isValid, reason = check_record(seen)
        if not isValid:
            failures.append(f'shared file is torn: {reason}')
            continue
        # A writer's sequence can only grow in time, so seeing it shrink means a stale or reordered read
        if seen['sequence'] < lastSequence.get(seen['writer'], -1):
            failures.append(f"shared file went back in time for writer {seen['writer']}")
        lastSequence[seen['writer']] = max(seen['sequence'], lastSequence.get(seen['writer'], -1))
    return failures


def fight_expected_files(writerIds, steps, sharedName='shared/hot'):
    """
    Lists the files that must be tracked after fight_for_files ran for every writer.

    :Parameters:
        #. writerIds (list): Identities of all writers.
        #. steps (int): Number of files created by each writer.
        #. sharedName (str): Relative path of the shared file.

    :Returns:
        #. expected (set): Relative paths that must be tracked, nothing more, nothing less.
    """
    expected = set([sharedName])
    for writerId in writerIds:
        for step in range(steps):
            expected.add(f'own/{writerId}/f{step}')
    return expected
