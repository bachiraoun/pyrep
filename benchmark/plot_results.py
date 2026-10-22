"""
Draws latency graphs from the Markdown tables written by the ladder benchmark.
"""
import os
import math
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter, ScalarFormatter

PERCENTILE_COLUMNS   = ('p50 ms', 'p95 ms', 'max ms')
REFERENCE_LATENCY_MS = 1000
SPLIT_TOTAL_THREADS  = 64
COMPARE_PROCESSES    = 16
COMPARE_TOTALS       = (16, 64, 256)


def read_tables(path):
    """
    Reads every scenario table of a Markdown results file.

    :Parameters:
        #. path (str): The Markdown file written by the ladder benchmark.

    :Returns:
        #. tables (dict): Scenario name mapped to a list of row dictionaries keyed by column title.
    """
    tables   = {}
    scenario = None
    titles   = None
    with open(path) as fd:
        for line in fd:
            line = line.strip()
            if line.startswith('## '):
                scenario = line[3:]
                tables[scenario] = []
            elif line.startswith('| processes'):
                titles = [cell.strip() for cell in line.strip('|').split('|')]
            elif line.startswith('|') and not line.startswith('|---') and titles is not None and scenario is not None:
                cells = [cell.strip() for cell in line.strip('|').split('|')]
                if len(cells) == len(titles) and cells[3] != '' and not cells[3].startswith('not run'):
                    tables[scenario].append(dict(zip(titles, cells)))
    return tables


def format_milliseconds(value, position):
    """
    Writes a latency tick as milliseconds below one second and as seconds above.

    :Parameters:
        #. value (float): The latency in milliseconds.
        #. position (int): Tick position, required by matplotlib and unused.

    :Returns:
        #. label (str): The tick text, such as `10 ms` or `1 s`.
    """
    if value >= 1000:
        return f'{value / 1000:g} s'
    return f'{value:g} ms'


def apply_latency_axis(axis):
    """
    Gives an axis a logarithmic latency scale with readable ticks and a dashed line at one second.

    :Parameters:
        #. axis (matplotlib.axes.Axes): The axis to set up.
    """
    axis.set_yscale('log')
    # Ticks at 1, 2 and 5 of every decade, so that a narrow range still gets labels
    axis.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    axis.yaxis.set_major_formatter(FuncFormatter(format_milliseconds))
    axis.yaxis.set_minor_formatter(NullFormatter())
    axis.axhline(REFERENCE_LATENCY_MS, color='gray', linestyle='--', linewidth=1)
    axis.grid(True, which='both', alpha=0.3)


def apply_rate_axis(axis):
    """
    Gives an axis a logarithmic operations-per-second scale with plain number labels.

    :Parameters:
        #. axis (matplotlib.axes.Axes): The axis to set up.
    """
    axis.set_yscale('log')
    axis.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, position: f'{value:g}'))
    axis.yaxis.set_minor_formatter(NullFormatter())
    axis.set_ylabel('operations per second (log scale)')
    axis.grid(True, which='both', alpha=0.3)


def apply_thread_axis(axis, threadCounts):
    """
    Gives an axis a logarithmic threads-per-process scale with a tick at every measured size.

    :Parameters:
        #. axis (matplotlib.axes.Axes): The axis to set up.
        #. threadCounts (list): The measured numbers of threads in each process.
    """
    axis.set_xscale('log')
    axis.set_xticks(sorted(set(threadCounts)))
    axis.xaxis.set_major_formatter(ScalarFormatter())
    axis.xaxis.set_minor_formatter(NullFormatter())
    axis.set_xlabel('threads in each process')


def list_operations(rows):
    """
    Lists the timed operations of a scenario in the order of the table.

    :Parameters:
        #. rows (list): Row dictionaries of the scenario table.

    :Returns:
        #. operations (list): Operation names without duplicates.
    """
    operations = []
    for row in rows:
        if row['operation'] not in operations:
            operations.append(row['operation'])
    return operations


def list_panels(tables):
    """
    Lists every scenario and operation pair with its rows.

    :Parameters:
        #. tables (dict): Scenario name mapped to its row dictionaries.

    :Returns:
        #. panels (list): Tuples of scenario, operation and the rows of that operation.
    """
    panels = []
    for scenario, rows in tables.items():
        for operation in list_operations(rows):
            panels.append((scenario, operation, [row for row in rows if row['operation'] == operation]))
    return panels


def first_operation_rows(rows):
    """
    Keeps the rows of the first operation, because operations per second is repeated on every operation row.

    :Parameters:
        #. rows (list): Row dictionaries of the scenario table.

    :Returns:
        #. selected (list): The rows of the first operation.
    """
    first = list_operations(rows)[0]
    return [row for row in rows if row['operation'] == first]


def draw_figure_legend(figure, axis):
    """
    Puts the legend of an axis at the right of the figure, where it hides no data.

    :Parameters:
        #. figure (matplotlib.figure.Figure): The figure receiving the legend.
        #. axis (matplotlib.axes.Axes): The axis whose lines are named.
    """
    handles, labels = axis.get_legend_handles_labels()
    figure.legend(handles, labels, loc='center right')


def hide_unused_axes(axes, usedCount):
    """
    Hides the empty panels at the end of a grid.

    :Parameters:
        #. axes (numpy.ndarray): The grid of axes.
        #. usedCount (int): Number of panels that hold a drawing.
    """
    for axis in list(axes.flat)[usedCount:]:
        axis.set_visible(False)


def draw_scenario(scenario, rows, outputPath):
    """
    Draws p50, p95 and max latency of one scenario against threads in each process, one line for each number of processes.

    :Parameters:
        #. scenario (str): The scenario name, used in the panel titles.
        #. rows (list): Row dictionaries of the scenario table.
        #. outputPath (str): The PNG file to write.
    """
    operations    = list_operations(rows)
    processCounts = sorted({int(row['processes']) for row in rows})
    figure, axes  = plt.subplots(len(operations), len(PERCENTILE_COLUMNS), figsize=(15, 3.4 * len(operations)),
                                 sharey='all', squeeze=False)
    for rowIndex, operation in enumerate(operations):
        for columnIndex, column in enumerate(PERCENTILE_COLUMNS):
            axis = axes[rowIndex, columnIndex]
            for processCount in processCounts:
                selected = [row for row in rows if row['operation'] == operation and int(row['processes']) == processCount]
                axis.plot([int(row['threads each']) for row in selected], [float(row[column]) for row in selected],
                          marker='o', label=f'{processCount} processes')
            apply_latency_axis(axis)
            apply_thread_axis(axis, [int(row['threads each']) for row in rows])
            axis.set_title(f'{scenario}: {operation}, {column}')
    draw_figure_legend(figure, axes[0, 0])
    figure.tight_layout(rect=(0, 0, 0.9, 1))
    figure.savefig(outputPath, dpi=110)
    plt.close(figure)


def draw_throughput(tables, outputPath):
    """
    Draws operations per second against threads in each process for every scenario.

    :Parameters:
        #. tables (dict): Scenario name mapped to its row dictionaries.
        #. outputPath (str): The PNG file to write.
    """
    columns      = 3
    rowCount     = math.ceil(len(tables) / columns)
    figure, axes = plt.subplots(rowCount, columns, figsize=(15, 4.2 * rowCount), squeeze=False)
    for axis, (scenario, rows) in zip(axes.flat, tables.items()):
        selectedRows = first_operation_rows(rows)
        for processCount in sorted({int(row['processes']) for row in selectedRows}):
            selected = [row for row in selectedRows if int(row['processes']) == processCount]
            axis.plot([int(row['threads each']) for row in selected], [float(row['ops/s']) for row in selected],
                      marker='o', label=f'{processCount} processes')
        apply_rate_axis(axis)
        axis.set_title(scenario)
        apply_thread_axis(axis, [int(row['threads each']) for row in selectedRows])
    draw_figure_legend(figure, axes[0, 0])
    hide_unused_axes(axes, len(tables))
    figure.tight_layout(rect=(0, 0, 0.9, 1))
    figure.savefig(outputPath, dpi=110)
    plt.close(figure)


def draw_splits(tables, outputPath):
    """
    Draws p50 and p95 latency of the same total thread count split in different ways between processes and threads.

    :Parameters:
        #. tables (dict): Scenario name mapped to its row dictionaries.
        #. outputPath (str): The PNG file to write.
    """
    panels       = list_panels(tables)
    columns      = 4
    rowCount     = math.ceil(len(panels) / columns)
    figure, axes = plt.subplots(rowCount, columns, figsize=(16, 3.8 * rowCount), squeeze=False)
    for axis, (scenario, operation, rows) in zip(axes.flat, panels):
        selected  = [row for row in rows if int(row['total threads']) == SPLIT_TOTAL_THREADS]
        positions = list(range(len(selected)))
        axis.bar([position - 0.2 for position in positions], [float(row['p50 ms']) for row in selected], width=0.4, log=True, label='p50 ms')
        axis.bar([position + 0.2 for position in positions], [float(row['p95 ms']) for row in selected], width=0.4, log=True, label='p95 ms')
        axis.set_xticks(positions)
        axis.set_xticklabels([f"{row['processes']}x{row['threads each']}" for row in selected])
        axis.set_xlabel('processes x threads each')
        axis.set_title(f'{scenario}: {operation}')
        apply_latency_axis(axis)
    axes[0, 0].legend()
    hide_unused_axes(axes, len(panels))
    figure.suptitle(f'{SPLIT_TOTAL_THREADS} total threads split in different ways')
    figure.tight_layout()
    figure.savefig(outputPath, dpi=110)
    plt.close(figure)


def find_row(rows, processCount, totalThreads):
    """
    Finds the row of one size.

    :Parameters:
        #. rows (list): Row dictionaries of one operation.
        #. processCount (int): Number of processes.
        #. totalThreads (int): Total number of threads.

    :Returns:
        #. row (dict): The matching row.

    :Raises:
        #. ValueError: If the size is not in the results.
    """
    for row in rows:
        if int(row['processes']) == processCount and int(row['total threads']) == totalThreads:
            return row
    raise ValueError(f'Size with {processCount} processes and {totalThreads} total threads is not in the results.')


def draw_comparison(tables, outputPath):
    """
    Draws p50 latency and operations per second of every scenario at the same sizes side by side.

    :Parameters:
        #. tables (dict): Scenario name mapped to its row dictionaries.
        #. outputPath (str): The PNG file to write.
    """
    panels                          = list_panels(tables)
    figure, (latencyAxis, rateAxis) = plt.subplots(1, 2, figsize=(15, 5.5))
    width = 0.8 / len(COMPARE_TOTALS)
    for index, totalThreads in enumerate(COMPARE_TOTALS):
        shift = (index - 0.5 * (len(COMPARE_TOTALS) - 1)) * width
        latencyAxis.bar([position + shift for position in range(len(panels))],
                        [float(find_row(rows, COMPARE_PROCESSES, totalThreads)['p50 ms']) for _, _, rows in panels],
                        width=width, log=True, label=f'{totalThreads} threads')
        rateAxis.bar([position + shift for position in range(len(tables))],
                     [float(find_row(first_operation_rows(rows), COMPARE_PROCESSES, totalThreads)['ops/s']) for rows in tables.values()],
                     width=width, log=True, label=f'{totalThreads} threads')
    latencyAxis.set_xticks(range(len(panels)))
    latencyAxis.set_xticklabels([f'{scenario}: {operation}' for scenario, operation, _ in panels], rotation=45, ha='right')
    latencyAxis.set_title(f'p50 latency with {COMPARE_PROCESSES} processes')
    apply_latency_axis(latencyAxis)
    rateAxis.set_xticks(range(len(tables)))
    rateAxis.set_xticklabels(list(tables), rotation=45, ha='right')
    rateAxis.set_title(f'operations per second with {COMPARE_PROCESSES} processes')
    apply_rate_axis(rateAxis)
    # Headroom above the bars keeps the legend off them
    latencyAxis.set_ylim(top=latencyAxis.get_ylim()[1] * 5)
    latencyAxis.legend(ncol=len(COMPARE_TOTALS), loc='upper left')
    figure.tight_layout()
    figure.savefig(outputPath, dpi=110)
    plt.close(figure)


def main():
    """
    Parses the command line and writes one PNG file per scenario plus three comparison graphs.
    """
    parser = argparse.ArgumentParser(description='Draw latency graphs from the ladder benchmark Markdown file.')
    parser.add_argument('markdown', help='file written by bench_ladder.py --markdown')
    parser.add_argument('--output-dir', default='docs/source/benchmark_images', help='folder receiving the PNG files')
    options = parser.parse_args()
    os.makedirs(options.output_dir, exist_ok=True)
    tables = read_tables(options.markdown)
    for scenario, rows in tables.items():
        draw_scenario(scenario, rows, os.path.join(options.output_dir, f'{scenario}.png'))
    draw_throughput(tables, os.path.join(options.output_dir, 'throughput.png'))
    draw_splits(tables, os.path.join(options.output_dir, 'splits.png'))
    draw_comparison(tables, os.path.join(options.output_dir, 'comparison.png'))


if __name__ == '__main__':
    main()
