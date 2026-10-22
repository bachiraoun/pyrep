"""
Benchmarks many processes, each running many threads, that fight over the same repository files.
"""
import os
import sys
import json
import time
import argparse
import threading
import resource
import multiprocessing

# The benchmark reuses the self-verifying records and the disk audit of the test suite
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests'))

from pyrep import Repository
from pyrep.__pkginfo__ import __version__ as pyrepVersion

from helpers import TemporaryRepository, audit_repository, check_record, make_record, run_in_processes

HOT_NAME      = 'shared/hot'
SCENARIOS     = ('read_same', 'update_same', 'read_own', 'update_own', 'create_unique', 'mixed')
LOCK_TIMEOUT  = 600
BARRIER_TIMEOUT = 900


def percentile(values, fraction):
    """
    Returns the value below which the given fraction of the values lie.

    :Parameters:
        #. values (list): Numbers to rank, it can be empty.
        #. fraction (float): Fraction between 0 and 1.

    :Returns:
        #. value (float): The percentile, 0.0 when there are no values.
    """
    if len(values) == 0:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def run_operation(repo, scenario, writerId, step, recordSize, latencies, failures):
    """
    Runs one step of a scenario, times every repository call and checks what it reads.

    :Parameters:
        #. repo (pyrep.Repository): The repository instance of this thread.
        #. scenario (str): One of SCENARIOS.
        #. writerId (str): Identity of this thread, unique across processes.
        #. step (int): Step number of this thread.
        #. recordSize (int): Number of items in the shared record.
        #. latencies (dict): Maps an operation name to the list of its durations in seconds.
        #. failures (list): Receives a description of every violated expectation.
    """
    def timed(name, call, *args, **kwargs):
        begin = time.perf_counter()
        outcome = call(*args, **kwargs)
        latencies.setdefault(name, []).append(time.perf_counter() - begin)
        return outcome

    if scenario == 'read_own':
        try:
            seen = timed('pull_own', repo.pull_file, f'own/{writerId}/seed')
            isValid, reason = check_record(seen)
            if isValid is False or seen['writer'] != writerId:
                failures.append(f'own file is wrong: {reason}')
        except Exception as err:
            failures.append(f'pull of own file failed: {str(err)[:150]}')
    if scenario == 'update_own':
        succeeded, message = timed('update_own', repo.update_file, make_record(writerId, step + 1), f'own/{writerId}/seed', raiseError=False)
        if succeeded is False:
            failures.append(f'update of own file failed: {message}')
    if scenario in ('read_same', 'mixed'):
        try:
            seen = timed('pull_shared', repo.pull_file, HOT_NAME)
            isValid, reason = check_record(seen)
            if isValid is False:
                failures.append(f'shared file is torn: {reason}')
        except Exception as err:
            failures.append(f'pull failed: {str(err)[:150]}')
    if scenario in ('update_same', 'mixed'):
        succeeded, message = timed('update_shared', repo.update_file, make_record(writerId, step, size=recordSize),
                                   HOT_NAME, raiseError=False)
        if succeeded is False:
            failures.append(f'update failed: {message}')
    if scenario in ('create_unique', 'mixed'):
        relative = f'own/{writerId}/f{step}'
        succeeded, message = timed('dump_own', repo.dump_file, make_record(writerId, step), relative, raiseError=False)
        if succeeded is False:
            failures.append(f'dump failed: {message}')


def bench_worker(path, processIndex, threadCount, steps, scenario, recordSize, instancePerThread, processBarrier, resultQueue):
    """
    Process body: runs the writer threads of one process and reports their timings.

    :Parameters:
        #. path (str): The repository path.
        #. processIndex (int): Index of this process.
        #. threadCount (int): Number of threads.
        #. steps (int): Number of steps per thread.
        #. scenario (str): One of SCENARIOS.
        #. recordSize (int): Number of items in the shared record.
        #. instancePerThread (bool): Whether every thread has its own Repository instance.
        #. processBarrier (multiprocessing.Barrier): Releases all the processes at the same moment, once every one of them is ready.
        #. resultQueue (multiprocessing.Queue): Receives the result dictionary.
    """
    instanceCount = threadCount if instancePerThread else 1
    instances     = [Repository(path, timeout=LOCK_TIMEOUT) for _ in range(instanceCount)]
    latencies     = {}
    failures      = []
    lock          = threading.Lock()

    threadBarrier = threading.Barrier(threadCount)

    def session(threadIndex):
        writerId     = f'p{processIndex}t{threadIndex}'
        ownLatencies = {}
        ownFailures  = []
        repo         = instances[threadIndex % instanceCount]
        threadBarrier.wait(timeout=BARRIER_TIMEOUT)
        for step in range(steps):
            run_operation(repo, scenario, writerId, step, recordSize, ownLatencies, ownFailures)
        with lock:
            for name, values in ownLatencies.items():
                latencies.setdefault(name, []).extend(values)
            failures.extend(ownFailures)

    # Every process waits for all the others, so that all contenders really start together
    processBarrier.wait(timeout=BARRIER_TIMEOUT)
    begin   = time.perf_counter()
    threads = [threading.Thread(target=session, args=(index,)) for index in range(threadCount)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed = time.perf_counter() - begin
    for instance in instances:
        instance.close()
    peakMemory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes, Linux reports kilobytes
    peakBytes  = peakMemory if sys.platform == 'darwin' else peakMemory * 1024
    resultQueue.put({'process': processIndex, 'elapsed': elapsed, 'latencies': latencies, 'failures': failures[:20],
                     'failureCount': len(failures), 'peakBytes': peakBytes})


def run_scenario(scenario, processCount, threadCount, steps, recordSize, instancePerThread):
    """
    Runs one scenario against a fresh repository and summarizes it.

    :Parameters:
        #. scenario (str): One of SCENARIOS.
        #. processCount (int): Number of processes.
        #. threadCount (int): Number of threads in each process.
        #. steps (int): Number of steps per thread.
        #. recordSize (int): Number of items in the shared record.
        #. instancePerThread (bool): Whether every thread has its own Repository instance.

    :Returns:
        #. summary (dict): Throughput, latency percentiles per operation, failures, disk problems and the peak memory of the biggest process.
    """
    with TemporaryRepository(timeout=LOCK_TIMEOUT) as temporary:
        temporary.repo.dump_file(make_record('seed', 0, size=recordSize), HOT_NAME)
        if scenario in ('read_own', 'update_own'):
            # Every thread owns one file, created here so that the timed part only reads or updates it
            for index in range(processCount):
                for threadIndex in range(threadCount):
                    writerId = f'p{index}t{threadIndex}'
                    temporary.repo.dump_file(make_record(writerId, 0), f'own/{writerId}/seed')
        processBarrier = multiprocessing.get_context('spawn').Barrier(processCount)
        args    = [(temporary.path, index, threadCount, steps, scenario, recordSize, instancePerThread, processBarrier)
                   for index in range(processCount)]
        results = run_in_processes(bench_worker, args, timeoutSeconds=3600)
        merged  = {}
        for result in results:
            for name, values in result['latencies'].items():
                merged.setdefault(name, []).extend(values)
        wallTime = max(result['elapsed'] for result in results)
        problems = audit_repository(temporary.path)
    operations = {}
    for name, values in merged.items():
        operations[name] = {'count': len(values), 'p50_ms': 1000 * percentile(values, 0.5),
                            'p95_ms': 1000 * percentile(values, 0.95), 'p99_ms': 1000 * percentile(values, 0.99),
                            'max_ms': 1000 * max(values)}
    totalCount = sum(item['count'] for item in operations.values())
    return {'scenario': scenario, 'processes': processCount, 'threads': threadCount, 'steps': steps, 'wall_seconds': wallTime,
            'operations_per_second': totalCount / wallTime, 'operations': operations,
            'failures': sum(result['failureCount'] for result in results),
            'failure_samples': [text for result in results for text in result['failures']][:5],
            'disk_problems': problems, 'peak_process_bytes': max(result['peakBytes'] for result in results)}


def print_summary(summary):
    """
    Prints one scenario summary as a small table.

    :Parameters:
        #. summary (dict): The result of run_scenario.
    """
    print(f"\n{summary['scenario']}: {summary['processes']} processes x {summary['threads']} threads, "
          f"{summary['wall_seconds']:.1f} s, {summary['operations_per_second']:.0f} operations/s")
    print(f"  {'operation':<16}{'count':>8}{'p50 ms':>10}{'p95 ms':>10}{'p99 ms':>10}{'max ms':>10}")
    for name, item in sorted(summary['operations'].items()):
        print(f"  {name:<16}{item['count']:>8}{item['p50_ms']:>10.1f}{item['p95_ms']:>10.1f}"
              f"{item['p99_ms']:>10.1f}{item['max_ms']:>10.1f}")
    verdict = 'OK' if summary['failures'] == 0 and len(summary['disk_problems']) == 0 else 'PROBLEMS'
    print(f"  integrity: {verdict} ({summary['failures']} failed expectations, {len(summary['disk_problems'])} disk problems)")
    for text in summary['failure_samples']:
        print(f'    {text}')


def main():
    """
    Parses the command line, runs the chosen scenarios and prints the results.

    :Returns:
        #. exitCode (int): 0 when every scenario kept its integrity, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description='Benchmark many processes and threads fighting over one repository.')
    parser.add_argument('--processes', type=int, default=100, help='number of processes (default 100)')
    parser.add_argument('--threads', type=int, default=10, help='threads per process (default 10)')
    parser.add_argument('--steps', type=int, default=3, help='steps per thread (default 3)')
    parser.add_argument('--record-size', type=int, default=2000, help='items in the shared record (default 2000)')
    parser.add_argument('--scenarios', nargs='+', choices=SCENARIOS, default=list(SCENARIOS), help='scenarios to run')
    parser.add_argument('--instance-per-thread', action='store_true', help='give every thread its own Repository instance')
    parser.add_argument('--json', default=None, help='file receiving the results as JSON')
    options      = parser.parse_args()
    instanceMode = 'one per thread' if options.instance_per_thread else 'one per process'
    print(f'python {sys.version.split()[0]} on {sys.platform}, pyrep {pyrepVersion}')
    print(f'processes={options.processes} threads={options.threads} steps={options.steps} '
          f'recordSize={options.record_size} instances={instanceMode}')
    print(f'{options.processes * options.threads} concurrent threads in total, scenarios: {", ".join(options.scenarios)}')
    summaries = []
    for scenario in options.scenarios:
        print(f'\nrunning {scenario}, every process waits for the others before the clock starts ...', flush=True)
        summary = run_scenario(scenario, options.processes, options.threads, options.steps, options.record_size,
                               options.instance_per_thread)
        print_summary(summary)
        summaries.append(summary)
    if options.json is not None:
        with open(options.json, 'w') as fd:
            json.dump(summaries, fd, indent=2)
    hasProblems = any(item['failures'] > 0 or len(item['disk_problems']) > 0 for item in summaries)
    return 1 if hasProblems else 0


if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
