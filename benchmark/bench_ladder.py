"""
Runs the contention benchmark on a ladder of sizes, from one instance to 500 processes with 10 threads each, for
reading, updating and writing, and prints the results as Markdown tables that can go into the documentation.

.. code-block:: python

    python benchmark/bench_ladder.py \
        --configs 1x1 1x4 1x16 1x64 1x128 \
                  2x1 2x4 2x16 2x64 2x128 \
                  4x1 4x4 4x16 4x64 4x128 \
                  8x1 8x4 8x16 8x64 8x128 \
                  16x1 16x4 16x16 16x64 \
                  32x1 32x4 32x16 32x32 \
                  64x1 64x4 64x16 \
                  128x1 128x4 128x8 \
        --max-total-threads 1024 \
        --min-operations 1000 \
        --markdown results.md --json results.json

    python benchmark/plot_results.py results.md

"""
import os
import sys
import json
import math
import time
import argparse
import platform
import multiprocessing

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyrep.__pkginfo__ import __version__ as pyrepVersion

from bench_contention import SCENARIOS, run_scenario

DEFAULT_CONFIGS        = ('1x1', '1x10', '1x100', '1x500', '1x1000','10x1', '10x10', '10x50', '10x100', '50x1', '50x10', '50x20', '100x1', '100x5', '100x10', '500x1','500x2','1000x1')
MEMORY_BUDGET_FRACTION = 0.6
FILES_PER_PROCESS      = 12


def parse_config(text):
    """
    Reads a size written as processes x threads.

    :Parameters:
        #. text (str): The size, such as 100x10 for 100 processes with 10 threads each.

    :Returns:
        #. processCount (int): Number of processes.
        #. threadCount (int): Number of threads in each process.

    :Raises:
        #. ValueError: If the text is not two positive integers separated by x.
    """
    parts = text.lower().split('x')
    if len(parts) != 2 or not all(part.isdigit() and int(part) > 0 for part in parts):
        raise ValueError(f"'{text}' is not a size, write it as processes x threads such as 100x10")
    return int(parts[0]), int(parts[1])


def raise_file_limit(processCount):
    """
    Raises the limit of open files of this process, which every started process inherits, as far as the system allows.

    :Parameters:
        #. processCount (int): Number of processes that will run.

    :Returns:
        #. limit (None, int): The limit now in force, None on systems without such a limit.
    """
    try:
        import resource
    except ImportError:
        return None
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    wanted = processCount * FILES_PER_PROCESS
    if hard != resource.RLIM_INFINITY:
        wanted = min(wanted, hard)
    if soft != resource.RLIM_INFINITY and soft < wanted:
        resource.setrlimit(resource.RLIMIT_NOFILE, (wanted, hard))
        soft = wanted
    return soft


def measure_process_memory(scenario, recordSize, instancePerThread, threadCount):
    """
    Measures the peak memory of one process running the given number of threads.

    :Parameters:
        #. scenario (str): One of SCENARIOS.
        #. recordSize (int): Number of items in the shared record.
        #. instancePerThread (bool): Whether every thread has its own Repository instance.
        #. threadCount (int): Number of threads in the measured process.

    :Returns:
        #. peakBytes (int): Peak memory of the single process, in bytes.
    """
    summary = run_scenario(scenario, 1, threadCount, 3, recordSize, instancePerThread)
    return summary['peak_process_bytes']


def get_memory_budget():
    """
    Gives the memory this benchmark may use, a fixed fraction of the physical memory.

    :Returns:
        #. budget (None, int): Bytes allowed, None when the memory size cannot be read.
    """
    try:
        totalBytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    except (ValueError, OSError, AttributeError):
        return None
    return int(totalBytes * MEMORY_BUDGET_FRACTION)


def build_rows(summary):
    """
    Turns the summary of one run into one table row per timed operation.

    :Parameters:
        #. summary (dict): The result of run_scenario.

    :Returns:
        #. rows (list): Dictionaries holding the size, the operation and its numbers.
    """
    rows = []
    for name, item in sorted(summary['operations'].items()):
        rows.append({'processes': summary['processes'], 'threads': summary['threads'],
                     'total_threads': summary['processes'] * summary['threads'], 'operation': name,
                     'count': item['count'], 'wall_seconds': summary['wall_seconds'],
                     'operations_per_second': summary['operations_per_second'], 'p50_ms': item['p50_ms'],
                     'p95_ms': item['p95_ms'], 'p99_ms': item['p99_ms'], 'max_ms': item['max_ms'],
                     'integrity': 'OK' if summary['failures'] == 0 and len(summary['disk_problems']) == 0 else 'PROBLEMS'})
    return rows


def format_markdown(results, header):
    """
    Writes the results as one Markdown table per scenario.

    :Parameters:
        #. results (list): The dictionaries of every run, with the keys scenario, config, rows and error.
        #. header (list): Lines that describe the machine and the settings.

    :Returns:
        #. text (str): The Markdown document.
    """
    lines = ['# pyrep contention benchmark', ''] + header + ['- ops/s counts every timed operation of the run, the latencies are per operation', '']
    for scenario in SCENARIOS:
        runs = [item for item in results if item['scenario'] == scenario]
        if len(runs) == 0:
            continue
        lines += [f'## {scenario}', '',
                  '| processes | threads each | total threads | operation | operations | wall s | ops/s | p50 ms | p95 ms | p99 ms | max ms | integrity |',
                  '|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|']
        for run in runs:
            if run['error'] is not None:
                processCount, threadCount = run['config']
                lines.append(f"| {processCount} | {threadCount} | {processCount * threadCount} | not run: {run['error']} | | | | | | | | |")
                continue
            for row in run['rows']:
                lines.append(f"| {row['processes']} | {row['threads']} | {row['total_threads']} | {row['operation']} | {row['count']} | "
                             f"{row['wall_seconds']:.1f} | {row['operations_per_second']:.0f} | {row['p50_ms']:.1f} | {row['p95_ms']:.1f} | "
                             f"{row['p99_ms']:.1f} | {row['max_ms']:.1f} | {row['integrity']} |")
        lines.append('')
    return '\n'.join(lines)


def main():
    """
    Parses the command line and runs every size for every scenario, one after the other.

    :Returns:
        #. exitCode (int): 0 when every run kept its integrity, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description='Run the pyrep contention benchmark on a ladder of sizes.')
    parser.add_argument('--configs', nargs='+', default=list(DEFAULT_CONFIGS),
                        help='sizes written as processes x threads (default: %s)' % ' '.join(DEFAULT_CONFIGS))
    parser.add_argument('--scenarios', nargs='+', choices=SCENARIOS, default=list(SCENARIOS), help='scenarios to run')
    parser.add_argument('--steps', type=int, default=3, help='least number of steps of every thread (default 3)')
    parser.add_argument('--min-operations', type=int, default=300,
                        help='steps are raised until a run has this many operations per timed operation, so small sizes measure something (default 300)')
    parser.add_argument('--record-size', type=int, default=2000, help='items in the shared record (default 2000)')
    parser.add_argument('--instance-per-thread', action='store_true', help='give every thread its own Repository instance')
    parser.add_argument('--max-total-threads', type=int, default=2048,
                        help='sizes with more threads than this (processes x threads) are not run (default 2048)')
    parser.add_argument('--markdown', default=None, help='file receiving the tables')
    parser.add_argument('--json', default=None, help='file receiving the raw results')
    options = parser.parse_args()
    configs = [parse_config(text) for text in options.configs]
    biggest = max(processCount for processCount, _ in configs)
    fileLimit = raise_file_limit(biggest)
    header = [f'- pyrep {pyrepVersion}, python {platform.python_version()}, {platform.system()} {platform.release()} {platform.machine()}',
              f'- {os.cpu_count()} logical processors, open file limit {fileLimit}',
              f"- sizes: {', '.join(options.configs)}",
              f"- scenarios: {', '.join(options.scenarios)}",
              f"- instances: {'one per thread' if options.instance_per_thread else 'one per process'}; shared record of {options.record_size} items",
              f'- date: {time.strftime("%Y-%m-%d %H:%M")}']
    print('\n'.join(header))
    memoryLimit      = get_memory_budget()
    memoryPerProcess = {}
    results = []
    for scenario in options.scenarios:
        for processCount, threadCount in configs:
            totalThreads = processCount * threadCount
            steps = max(options.steps, math.ceil(options.min_operations / totalThreads))
            print(f'\n[{scenario}] {processCount} processes x {threadCount} threads, {steps} steps each ...', flush=True)
            entry = {'scenario': scenario, 'config': (processCount, threadCount), 'rows': [], 'error': None}
            skipReason = None
            if totalThreads > options.max_total_threads:
                skipReason = f'{totalThreads} threads, above the limit of {options.max_total_threads}'
            elif memoryLimit is not None:
                if threadCount not in memoryPerProcess:
                    memoryPerProcess[threadCount] = measure_process_memory(options.scenarios[0], options.record_size,
                                                                           options.instance_per_thread, threadCount)
                    print(f'One process with {threadCount} threads peaks at {memoryPerProcess[threadCount] / 1024 ** 2:.0f} MB', flush=True)
                neededBytes = processCount * memoryPerProcess[threadCount]
                if neededBytes > memoryLimit:
                    skipReason = f'needs {neededBytes / 1024 ** 3:.0f} GB, above the {memoryLimit / 1024 ** 3:.0f} GB budget'
            if skipReason is not None:
                entry['error'] = skipReason
                print(f"    not run: {entry['error']}", flush=True)
                results.append(entry)
                continue
            try:
                summary = run_scenario(scenario, processCount, threadCount, steps, options.record_size, options.instance_per_thread)
                entry['rows'] = build_rows(summary)
                entry['summary'] = summary
                verdict = 'OK' if summary['failures'] == 0 and len(summary['disk_problems']) == 0 else 'PROBLEMS'
                print(f"    {summary['wall_seconds']:.1f} s, {summary['operations_per_second']:.0f} operations/s, integrity {verdict}", flush=True)
            except Exception as err:
                entry['error'] = str(err)[:120]
                print(f"    not run: {entry['error']}", flush=True)
            results.append(entry)
    text = format_markdown(results, header)
    print('\n' + text)
    if options.markdown is not None:
        with open(options.markdown, 'w') as fd:
            fd.write(text + '\n')
    if options.json is not None:
        with open(options.json, 'w') as fd:
            json.dump(results, fd, indent=2, default=str)
    hasProblems = any(item['error'] is not None or any(row['integrity'] != 'OK' for row in item['rows']) for item in results)
    return 1 if hasProblems else 0


if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
