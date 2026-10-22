Contention benchmark
====================

The benchmark starts many processes, each running many threads, that all work on the same repository.
Every run checks the repository afterwards, and the integrity column reads OK when nothing was lost or corrupted.

- pyrep 4.0.0, python 3.12.10, Darwin 25.3.0 x86_64
- 16 logical processors, open file limit 2560
- One Repository instance per process; shared record of 2000 items
- Sizes from 1 to 128 processes and from 1 to 128 threads each, up to 1024 threads in total
- Date: 2026-10-22
- ops/s counts every timed operation of the run. The latencies are per operation, in milliseconds.
- The scenario graphs show p50, p95 and max latency, one line for each number of processes, on logarithmic axes. The dashed line marks one second. The tables also give p99.

.. code-block:: bash

    python3 benchmark/bench_ladder.py \
         --configs 1x1 1x4 1x16 1x64 1x128 2x1 2x4 2x16 2x64 2x128 \
                   4x1 4x4 4x16 4x64 4x128 8x1 8x4 8x16 8x64 8x128 \
                   16x1 16x4 16x16 16x64 32x1 32x4 32x16 32x32 \
                   64x1 64x4 64x16 128x1 128x4 128x8 \
         --max-total-threads 1024 --min-operations 1000 \
         --markdown results.md
    python3 benchmark/plot_results.py results.md


Scenarios
---------

In every scenario, each thread repeats its step many times. All threads of all processes start together.
*Shared* means every thread uses one file. *Own* means each thread has its own file.

.. csv-table::
    :header: "scenario", "what every thread does", "what it measures"
    :widths: 18, 47, 35

    read_same, "Reads the one shared file (``pull_file``).", "Many readers on one file."
    update_same, "Rewrites the one shared file (``update_file``).", "Many writers fighting for one file."
    read_own, "Reads its own file.", "Readers that never touch the same file."
    update_own, "Rewrites its own file.", "Writers that never touch the same file."
    create_unique, "Creates a new file of its own at every step (``dump_file``).", "Many writers adding files to the repository."
    mixed, "At every step reads the shared file, rewrites it, then creates a new file of its own.", "All three operations together."

Every read checks that the record is complete and not a mix of two writes. Every run ends with an audit of the files on disk.
The integrity column reads OK when all those checks passed.

Operation names in the tables: ``pull_shared`` reads the shared file, ``pull_own`` reads the thread's own file,
``update_shared`` and ``update_own`` rewrite them, and ``dump_own`` creates a new file.

Latency columns: ``p50`` is the typical time, half of the operations were faster. ``p95`` and ``p99`` are the times that
95 and 99 of every 100 operations stayed under, so they show the slow cases. ``max`` is the slowest single operation.

Comparisons
-----------

.. image:: benchmark_images/throughput.png
    :width: 100%
    :alt: Operations per second against threads in each process for every scenario

Operations per second against the number of threads in each process. A line that stays flat means more threads add no work done.

.. image:: benchmark_images/splits.png
    :width: 100%
    :alt: Latency of 64 threads split in different ways between processes and threads

The same 64 threads split in different ways: 1 process of 64 threads, 16 processes of 4 threads, and 64 processes of 1 thread. It shows whether processes or threads are the better way to add load.

.. image:: benchmark_images/comparison.png
    :width: 100%
    :alt: Latency and operations per second of all scenarios at 16, 64 and 256 threads

All scenarios side by side at 16, 64 and 256 total threads, with 16 processes.

Every run records 1000 to 3072 operations of each timed operation, as the operations column shows. The percentiles and the slowest operation can therefore be compared between sizes. p99 is the time that 99 of every 100 operations stayed under.

Findings
--------

Every run kept its integrity, up to 128 processes and 1024 threads in total. Nothing was lost or corrupted.
Sizes above 1024 total threads were not run.

.. csv-table:: Operations per second
    :header: "scenario", "1 process, 1 thread", "best size", "best ops/s", "at 1024 threads"
    :widths: 20, 18, 22, 15, 25

    read_same, 476, "2 x 1", 631, "459 to 495"
    update_same, 239, "4 x 64", 259, "227 to 257"
    read_own, 726, "32 x 32", 4810, "2896 to 4810"
    update_own, 245, "8 x 4", 1329, "59 to 233"
    create_unique, 181, "2 x 1", 218, "97 to 100"
    mixed, 245, "32 x 1", 508, "223 to 262"

**One shared file is a queue.** In ``read_same`` and ``update_same`` the throughput stays flat at about 500 reads
and 250 updates per second, whatever the number of processes or threads. Every extra thread only lengthens the
queue, so the typical latency grows with the total thread count: about 2 ms per thread for reads and 4 ms per
thread for updates. With 1024 threads, a read takes about 2 s and an update about 4 s.

**Processes and threads cost the same on one file.** The splits graph shows 64 threads divided in different ways.
For ``read_same``, ``update_same`` and ``create_unique`` the latency is almost the same for 1 x 64, 16 x 4 and 64 x 1.

**Separate files scale with processes, not with threads.** ``read_own`` goes from 726 operations per second for
one thread to about 4500 with 16 processes, which is the number of logical processors of the machine.
More processes do not add anything: 128 x 4 reaches 2471. One process with 128 threads stays at 982.
At 64 threads, a read takes 62 ms in 1 x 64 and 13 ms in 16 x 4.

**Updating separate files stops scaling early.** ``update_own`` is fast up to 256 total threads
(for example 1329 operations per second at 8 x 4). From 512 threads on, the typical latency stays moderate
but the slowest operations wait very long: at 16 x 64 the p50 is 10 s and the p95 is 28 s, and throughput falls to 78
operations per second. 32 x 32 and 128 x 8 behave the same way. Heavy update loads are better kept below
about 256 threads.

**Creating files tops out near 200 per second.** ``create_unique`` gives about 200 files per second up to 32
threads and falls to about 100 at 1024 threads, where a creation takes about 9 s.

**In the mixed scenario, creating files is the slow part.** At 1024 threads the p50 is about 10 ms for reads and
updates, but 8.5 to 10 s for ``dump_own``. The p95 of reads and updates still reaches 3 to 5 s.

read_same
---------

.. image:: benchmark_images/read_same.png
    :width: 100%
    :alt: Latency percentiles of the read_same scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, pull_shared, 1000, 2.1, 476, 1.0, 1.5, 1.9, 2.7, OK
    1, 4, 4, pull_shared, 1000, 2.0, 502, 6.8, 7.9, 8.8, 10.3, OK
    1, 16, 16, pull_shared, 1008, 2.0, 507, 30.0, 34.2, 39.5, 40.5, OK
    1, 64, 64, pull_shared, 1024, 2.1, 486, 125.7, 147.7, 156.1, 157.6, OK
    1, 128, 128, pull_shared, 1024, 2.1, 494, 254.2, 259.0, 280.7, 300.7, OK
    2, 1, 2, pull_shared, 1000, 1.6, 631, 2.2, 3.2, 3.7, 4.7, OK
    2, 4, 8, pull_shared, 1000, 1.8, 546, 13.3, 16.1, 20.4, 24.4, OK
    2, 16, 32, pull_shared, 1024, 1.8, 557, 56.0, 59.2, 60.7, 70.6, OK
    2, 64, 128, pull_shared, 1024, 2.1, 497, 249.4, 269.6, 273.5, 274.0, OK
    2, 128, 256, pull_shared, 1024, 2.0, 501, 503.8, 518.8, 544.6, 564.6, OK
    4, 1, 4, pull_shared, 1000, 1.7, 575, 5.9, 7.5, 8.2, 9.0, OK
    4, 4, 16, pull_shared, 1008, 1.8, 565, 27.0, 29.9, 31.2, 35.6, OK
    4, 16, 64, pull_shared, 1024, 1.9, 539, 115.8, 121.6, 133.9, 147.1, OK
    4, 64, 256, pull_shared, 1024, 2.2, 465, 530.3, 541.0, 592.2, 614.0, OK
    4, 128, 512, pull_shared, 1536, 3.4, 449, 1109.9, 1150.3, 1199.0, 1231.5, OK
    8, 1, 8, pull_shared, 1000, 2.0, 512, 14.4, 17.1, 19.1, 21.4, OK
    8, 4, 32, pull_shared, 1024, 2.1, 497, 62.9, 68.4, 70.7, 73.0, OK
    8, 16, 128, pull_shared, 1024, 2.1, 484, 262.4, 274.7, 276.2, 276.7, OK
    8, 64, 512, pull_shared, 1536, 3.5, 440, 1082.6, 1236.8, 1268.2, 1302.7, OK
    8, 128, 1024, pull_shared, 3072, 6.7, 462, 2147.8, 2277.4, 2305.5, 2379.6, OK
    16, 1, 16, pull_shared, 1008, 2.0, 501, 29.4, 38.9, 40.7, 42.4, OK
    16, 4, 64, pull_shared, 1024, 1.9, 552, 113.0, 120.7, 134.4, 144.0, OK
    16, 16, 256, pull_shared, 1024, 2.1, 484, 509.8, 526.6, 527.6, 529.2, OK
    16, 64, 1024, pull_shared, 3072, 6.7, 459, 2217.0, 2293.3, 2322.2, 2415.2, OK
    32, 1, 32, pull_shared, 1024, 1.9, 544, 57.6, 62.1, 63.8, 65.2, OK
    32, 4, 128, pull_shared, 1024, 2.0, 521, 230.5, 251.6, 293.5, 301.3, OK
    32, 16, 512, pull_shared, 1536, 3.0, 505, 965.7, 1015.4, 1018.4, 1053.5, OK
    32, 32, 1024, pull_shared, 3072, 6.2, 493, 2000.6, 2118.6, 2123.2, 2150.4, OK
    64, 1, 64, pull_shared, 1024, 2.1, 478, 116.2, 130.6, 306.0, 344.6, OK
    64, 4, 256, pull_shared, 1024, 2.1, 498, 471.6, 582.7, 609.2, 619.5, OK
    64, 16, 1024, pull_shared, 3072, 6.2, 495, 1997.6, 2095.4, 2097.3, 2110.6, OK
    128, 1, 128, pull_shared, 1024, 2.5, 412, 238.1, 477.7, 733.8, 769.4, OK
    128, 4, 512, pull_shared, 1536, 3.4, 454, 1024.1, 1263.3, 1302.1, 1309.7, OK
    128, 8, 1024, pull_shared, 3072, 6.7, 461, 2079.7, 2262.0, 2310.2, 2319.6, OK

update_same
-----------

.. image:: benchmark_images/update_same.png
    :width: 100%
    :alt: Latency percentiles of the update_same scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, update_shared, 1000, 4.2, 239, 3.2, 3.9, 4.3, 96.8, OK
    1, 4, 4, update_shared, 1000, 3.9, 254, 14.8, 16.1, 17.1, 20.2, OK
    1, 16, 16, update_shared, 1008, 4.0, 252, 61.5, 66.9, 75.5, 87.0, OK
    1, 64, 64, update_shared, 1024, 4.1, 252, 250.2, 263.3, 271.4, 288.7, OK
    1, 128, 128, update_shared, 1024, 4.2, 244, 512.2, 533.7, 537.2, 590.9, OK
    2, 1, 2, update_shared, 1000, 4.0, 251, 7.0, 7.9, 9.2, 36.9, OK
    2, 4, 8, update_shared, 1000, 4.0, 252, 30.7, 32.8, 34.6, 36.8, OK
    2, 16, 32, update_shared, 1024, 4.1, 252, 125.0, 131.8, 137.1, 139.1, OK
    2, 64, 128, update_shared, 1024, 4.2, 242, 529.3, 550.5, 551.6, 552.5, OK
    2, 128, 256, update_shared, 1024, 4.3, 237, 1076.3, 1094.8, 1096.3, 1111.1, OK
    4, 1, 4, update_shared, 1000, 4.2, 240, 15.6, 16.9, 18.4, 28.2, OK
    4, 4, 16, update_shared, 1008, 4.0, 249, 62.0, 67.2, 100.3, 102.7, OK
    4, 16, 64, update_shared, 1024, 4.1, 251, 254.2, 268.2, 275.3, 276.1, OK
    4, 64, 256, update_shared, 1024, 4.0, 259, 1004.4, 1034.2, 1035.6, 1062.5, OK
    4, 128, 512, update_shared, 1536, 6.2, 249, 1969.3, 2175.1, 2179.9, 2218.9, OK
    8, 1, 8, update_shared, 1000, 4.2, 239, 32.2, 34.6, 47.0, 64.2, OK
    8, 4, 32, update_shared, 1024, 4.4, 235, 133.9, 144.5, 147.9, 150.9, OK
    8, 16, 128, update_shared, 1024, 4.4, 234, 527.8, 653.0, 656.6, 658.9, OK
    8, 64, 512, update_shared, 1536, 6.1, 252, 1964.1, 2152.4, 2155.8, 2262.2, OK
    8, 128, 1024, update_shared, 3072, 12.0, 257, 3875.3, 4257.7, 4264.7, 4348.0, OK
    16, 1, 16, update_shared, 1008, 4.2, 240, 65.6, 68.8, 74.6, 76.9, OK
    16, 4, 64, update_shared, 1024, 4.2, 241, 264.4, 279.9, 282.4, 282.9, OK
    16, 16, 256, update_shared, 1024, 4.1, 250, 1015.8, 1100.7, 1103.2, 1105.2, OK
    16, 64, 1024, update_shared, 3072, 12.3, 250, 4041.9, 4392.9, 4401.9, 4487.0, OK
    32, 1, 32, update_shared, 1024, 4.3, 236, 132.1, 135.2, 137.2, 204.6, OK
    32, 4, 128, update_shared, 1024, 4.3, 241, 528.8, 549.6, 561.5, 568.6, OK
    32, 16, 512, update_shared, 1536, 6.0, 254, 1982.7, 2132.2, 2134.1, 2136.6, OK
    32, 32, 1024, update_shared, 3072, 13.1, 235, 4299.1, 4566.1, 4575.4, 4577.4, OK
    64, 1, 64, update_shared, 1024, 5.2, 195, 301.9, 466.7, 490.1, 491.9, OK
    64, 4, 256, update_shared, 1024, 4.6, 221, 1114.2, 1266.6, 1274.6, 1280.4, OK
    64, 16, 1024, update_shared, 3072, 12.9, 238, 4122.5, 4593.0, 4600.0, 4614.6, OK
    128, 1, 128, update_shared, 1024, 5.2, 198, 585.5, 815.3, 944.7, 996.4, OK
    128, 4, 512, update_shared, 1536, 7.4, 207, 2377.3, 2624.8, 2668.1, 2685.5, OK
    128, 8, 1024, update_shared, 3072, 13.6, 227, 4279.7, 4732.5, 4770.4, 4774.1, OK

read_own
--------

.. image:: benchmark_images/read_own.png
    :width: 100%
    :alt: Latency percentiles of the read_own scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, pull_own, 1000, 1.4, 726, 1.1, 1.3, 1.5, 2.0, OK
    1, 4, 4, pull_own, 1000, 1.2, 855, 4.4, 4.9, 5.2, 7.1, OK
    1, 16, 16, pull_own, 1008, 1.1, 898, 16.8, 21.1, 24.8, 28.1, OK
    1, 64, 64, pull_own, 1024, 1.0, 988, 62.0, 76.9, 84.6, 93.7, OK
    1, 128, 128, pull_own, 1024, 1.0, 982, 122.3, 157.6, 166.9, 179.8, OK
    2, 1, 2, pull_own, 1000, 0.7, 1437, 1.1, 1.3, 1.4, 2.1, OK
    2, 4, 8, pull_own, 1000, 0.6, 1557, 4.8, 5.5, 6.3, 7.4, OK
    2, 16, 32, pull_own, 1024, 0.6, 1731, 17.6, 20.8, 22.2, 24.9, OK
    2, 64, 128, pull_own, 1024, 0.6, 1831, 66.8, 84.4, 89.9, 95.8, OK
    2, 128, 256, pull_own, 1024, 0.6, 1644, 140.0, 186.8, 206.0, 219.4, OK
    4, 1, 4, pull_own, 1000, 0.4, 2567, 1.3, 1.6, 1.8, 2.1, OK
    4, 4, 16, pull_own, 1008, 0.4, 2479, 6.0, 7.0, 7.6, 9.2, OK
    4, 16, 64, pull_own, 1024, 0.4, 2667, 22.6, 28.4, 30.8, 33.6, OK
    4, 64, 256, pull_own, 1024, 0.4, 2690, 87.9, 112.0, 121.7, 128.3, OK
    4, 128, 512, pull_own, 1536, 0.5, 2885, 158.9, 214.5, 231.1, 238.8, OK
    8, 1, 8, pull_own, 1000, 0.3, 3724, 1.8, 2.2, 2.6, 3.8, OK
    8, 4, 32, pull_own, 1024, 0.3, 3622, 8.2, 9.9, 10.7, 12.6, OK
    8, 16, 128, pull_own, 1024, 0.3, 4053, 29.7, 35.8, 38.3, 44.4, OK
    8, 64, 512, pull_own, 1536, 0.4, 4098, 111.3, 145.7, 157.8, 177.1, OK
    8, 128, 1024, pull_own, 3072, 0.8, 3786, 238.7, 324.9, 360.8, 429.1, OK
    16, 1, 16, pull_own, 1008, 0.2, 4527, 3.1, 3.9, 4.2, 5.7, OK
    16, 4, 64, pull_own, 1024, 0.2, 4536, 12.8, 19.1, 20.5, 25.3, OK
    16, 16, 256, pull_own, 1024, 0.2, 4585, 48.4, 74.7, 85.1, 91.5, OK
    16, 64, 1024, pull_own, 3072, 0.7, 4156, 189.2, 320.8, 383.4, 453.7, OK
    32, 1, 32, pull_own, 1024, 0.2, 4234, 6.9, 8.6, 9.7, 10.4, OK
    32, 4, 128, pull_own, 1024, 0.2, 4191, 25.0, 43.8, 46.5, 49.5, OK
    32, 16, 512, pull_own, 1536, 0.4, 3892, 105.4, 181.3, 197.0, 208.0, OK
    32, 32, 1024, pull_own, 3072, 0.6, 4810, 169.5, 276.6, 318.7, 376.3, OK
    64, 1, 64, pull_own, 1024, 0.2, 4163, 14.4, 19.2, 19.7, 21.4, OK
    64, 4, 256, pull_own, 1024, 0.2, 4280, 47.9, 89.9, 93.7, 101.0, OK
    64, 16, 1024, pull_own, 3072, 1.0, 2952, 203.3, 320.5, 345.0, 380.6, OK
    128, 1, 128, pull_own, 1024, 0.3, 3898, 34.8, 37.6, 38.1, 39.0, OK
    128, 4, 512, pull_own, 1536, 0.6, 2471, 116.4, 391.2, 404.7, 419.1, OK
    128, 8, 1024, pull_own, 3072, 1.1, 2896, 265.1, 434.9, 448.9, 458.1, OK

update_own
----------

.. image:: benchmark_images/update_own.png
    :width: 100%
    :alt: Latency percentiles of the update_own scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, update_own, 1000, 4.1, 245, 3.8, 4.2, 4.5, 5.3, OK
    1, 4, 4, update_own, 1000, 1.9, 525, 7.3, 8.1, 8.6, 9.4, OK
    1, 16, 16, update_own, 1008, 1.7, 598, 25.8, 29.5, 44.1, 48.5, OK
    1, 64, 64, update_own, 1024, 1.7, 614, 101.6, 119.5, 128.6, 137.3, OK
    1, 128, 128, update_own, 1024, 1.6, 624, 197.1, 235.2, 251.7, 262.2, OK
    2, 1, 2, update_own, 1000, 1.9, 522, 3.6, 3.8, 4.0, 18.2, OK
    2, 4, 8, update_own, 1000, 1.1, 906, 8.3, 9.2, 10.0, 36.9, OK
    2, 16, 32, update_own, 1024, 1.0, 1031, 30.2, 34.5, 35.9, 38.8, OK
    2, 64, 128, update_own, 1024, 1.1, 951, 125.3, 185.5, 197.6, 205.4, OK
    2, 128, 256, update_own, 1024, 1.0, 989, 243.6, 290.1, 311.8, 331.6, OK
    4, 1, 4, update_own, 1000, 1.0, 989, 3.8, 4.2, 4.4, 4.8, OK
    4, 4, 16, update_own, 1008, 0.8, 1234, 12.3, 14.0, 23.1, 24.6, OK
    4, 16, 64, update_own, 1024, 1.1, 902, 70.8, 84.8, 89.7, 97.8, OK
    4, 64, 256, update_own, 1024, 1.9, 526, 422.8, 817.1, 828.0, 843.2, OK
    4, 128, 512, update_own, 1536, 2.7, 567, 390.0, 1919.4, 1974.1, 2061.0, OK
    8, 1, 8, update_own, 1000, 0.8, 1278, 5.7, 6.3, 13.8, 30.4, OK
    8, 4, 32, update_own, 1024, 0.8, 1329, 22.5, 32.3, 36.7, 46.1, OK
    8, 16, 128, update_own, 1024, 1.2, 827, 124.1, 266.3, 286.6, 360.2, OK
    8, 64, 512, update_own, 1536, 6.5, 237, 917.7, 5275.8, 5291.5, 5326.1, OK
    8, 128, 1024, update_own, 3072, 13.2, 233, 600.9, 12139.6, 12252.6, 12482.1, OK
    16, 1, 16, update_own, 1008, 0.9, 1091, 11.3, 13.9, 149.4, 236.1, OK
    16, 4, 64, update_own, 1024, 1.1, 928, 69.6, 112.2, 150.1, 168.7, OK
    16, 16, 256, update_own, 1024, 3.0, 337, 688.3, 1665.7, 2129.0, 2385.0, OK
    16, 64, 1024, update_own, 3072, 39.5, 78, 10212.4, 28094.8, 28165.9, 28188.6, OK
    32, 1, 32, update_own, 1024, 0.9, 1166, 25.2, 40.3, 56.8, 90.8, OK
    32, 4, 128, update_own, 1024, 1.6, 630, 107.5, 366.6, 387.7, 403.2, OK
    32, 16, 512, update_own, 1536, 8.5, 181, 1489.1, 6902.6, 8022.8, 8376.9, OK
    32, 32, 1024, update_own, 3072, 40.2, 76, 8008.8, 30746.7, 30803.9, 30839.2, OK
    64, 1, 64, update_own, 1024, 1.3, 792, 63.8, 138.0, 200.8, 212.0, OK
    64, 4, 256, update_own, 1024, 2.9, 353, 529.4, 1821.6, 2364.0, 2427.6, OK
    64, 16, 1024, update_own, 3072, 29.6, 104, 7107.6, 21939.5, 22040.5, 22093.1, OK
    128, 1, 128, update_own, 1024, 1.8, 559, 97.7, 386.3, 504.8, 508.5, OK
    128, 4, 512, update_own, 1536, 7.8, 196, 1069.4, 6350.0, 6418.5, 6470.0, OK
    128, 8, 1024, update_own, 3072, 51.7, 59, 19963.1, 30595.3, 30691.5, 30729.8, OK

create_unique
-------------

.. image:: benchmark_images/create_unique.png
    :width: 100%
    :alt: Latency percentiles of the create_unique scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, dump_own, 1000, 5.5, 181, 5.2, 5.6, 5.8, 92.7, OK
    1, 4, 4, dump_own, 1000, 4.8, 208, 18.8, 19.6, 28.7, 34.8, OK
    1, 16, 16, dump_own, 1008, 4.8, 212, 74.0, 77.7, 96.7, 142.0, OK
    1, 64, 64, dump_own, 1024, 5.2, 196, 306.0, 387.0, 507.7, 549.4, OK
    1, 128, 128, dump_own, 1024, 5.5, 186, 629.8, 851.3, 1048.9, 1092.6, OK
    2, 1, 2, dump_own, 1000, 4.6, 218, 8.9, 9.4, 10.6, 24.7, OK
    2, 4, 8, dump_own, 1000, 4.6, 215, 36.7, 37.9, 38.7, 64.4, OK
    2, 16, 32, dump_own, 1024, 4.9, 210, 148.9, 154.5, 208.1, 253.4, OK
    2, 64, 128, dump_own, 1024, 5.5, 187, 626.7, 840.9, 1037.9, 1084.5, OK
    2, 128, 256, dump_own, 1024, 6.5, 159, 1395.7, 2084.7, 2303.7, 2372.5, OK
    4, 1, 4, dump_own, 1000, 4.7, 214, 18.3, 19.0, 19.9, 54.1, OK
    4, 4, 16, dump_own, 1008, 4.9, 207, 73.7, 77.2, 210.7, 211.8, OK
    4, 16, 64, dump_own, 1024, 5.0, 204, 299.0, 307.1, 466.0, 512.3, OK
    4, 64, 256, dump_own, 1024, 6.3, 161, 1398.1, 1986.2, 2232.9, 2288.0, OK
    4, 128, 512, dump_own, 1536, 11.5, 134, 3239.5, 4831.5, 5243.0, 5344.3, OK
    8, 1, 8, dump_own, 1000, 4.8, 207, 37.5, 42.3, 53.5, 77.8, OK
    8, 4, 32, dump_own, 1024, 5.0, 205, 152.0, 172.2, 220.1, 264.9, OK
    8, 16, 128, dump_own, 1024, 5.5, 185, 637.8, 820.4, 1022.2, 1070.0, OK
    8, 64, 512, dump_own, 1536, 11.8, 130, 3378.2, 4825.6, 5218.8, 5309.8, OK
    8, 128, 1024, dump_own, 3072, 31.8, 97, 9209.7, 13364.3, 14474.3, 14766.2, OK
    16, 1, 16, dump_own, 1008, 5.2, 193, 80.0, 86.9, 144.3, 145.2, OK
    16, 4, 64, dump_own, 1024, 5.6, 182, 320.8, 477.8, 507.7, 559.9, OK
    16, 16, 256, dump_own, 1024, 7.3, 141, 1570.2, 2357.8, 2605.2, 2656.2, OK
    16, 64, 1024, dump_own, 3072, 31.5, 97, 9182.8, 13512.4, 14629.4, 14885.4, OK
    32, 1, 32, dump_own, 1024, 5.1, 202, 151.1, 173.2, 231.8, 278.7, OK
    32, 4, 128, dump_own, 1024, 5.9, 175, 663.4, 862.5, 1061.5, 1111.4, OK
    32, 16, 512, dump_own, 1536, 11.7, 131, 3318.0, 4885.7, 5255.7, 5351.9, OK
    32, 32, 1024, dump_own, 3072, 30.6, 100, 8886.6, 12942.2, 13942.7, 14202.1, OK
    64, 1, 64, dump_own, 1024, 5.6, 182, 317.0, 485.4, 576.5, 613.0, OK
    64, 4, 256, dump_own, 1024, 7.2, 142, 1549.3, 2274.3, 2523.1, 2581.0, OK
    64, 16, 1024, dump_own, 3072, 31.3, 98, 8907.4, 13829.3, 14890.7, 15122.1, OK
    128, 1, 128, dump_own, 1024, 6.8, 150, 704.5, 1104.1, 1304.7, 1365.5, OK
    128, 4, 512, dump_own, 1536, 13.8, 111, 3909.7, 5975.6, 6447.0, 6564.9, OK
    128, 8, 1024, dump_own, 3072, 31.5, 98, 8849.6, 14183.0, 15236.8, 15482.1, OK

mixed
-----

.. image:: benchmark_images/mixed.png
    :width: 100%
    :alt: Latency percentiles of the mixed scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, dump_own, 1000, 12.3, 245, 4.7, 5.4, 5.8, 229.8, OK
    1, 1, 1, pull_shared, 1000, 12.3, 245, 1.4, 1.6, 1.8, 3.0, OK
    1, 1, 1, update_shared, 1000, 12.3, 245, 3.4, 3.9, 4.2, 15.5, OK
    1, 4, 4, dump_own, 1000, 9.3, 324, 20.2, 25.7, 26.7, 83.9, OK
    1, 4, 4, pull_shared, 1000, 9.3, 324, 7.1, 10.6, 11.7, 44.4, OK
    1, 4, 4, update_shared, 1000, 9.3, 324, 7.8, 10.1, 11.9, 42.0, OK
    1, 16, 16, dump_own, 1008, 9.7, 311, 138.9, 143.0, 216.9, 219.3, OK
    1, 16, 16, pull_shared, 1008, 9.7, 311, 3.3, 11.0, 35.6, 67.6, OK
    1, 16, 16, update_shared, 1008, 9.7, 311, 4.9, 10.4, 63.6, 81.3, OK
    1, 64, 64, dump_own, 1024, 10.2, 300, 608.7, 626.3, 743.9, 938.0, OK
    1, 64, 64, pull_shared, 1024, 10.2, 300, 3.1, 126.6, 235.6, 321.9, OK
    1, 64, 64, update_shared, 1024, 10.2, 300, 4.8, 241.1, 317.7, 336.5, OK
    1, 128, 128, dump_own, 1024, 10.8, 284, 1241.4, 1407.9, 1737.2, 1904.2, OK
    1, 128, 128, pull_shared, 1024, 10.8, 284, 3.3, 393.3, 535.9, 658.4, OK
    1, 128, 128, update_shared, 1024, 10.8, 284, 4.9, 576.2, 654.2, 673.9, OK
    2, 1, 2, dump_own, 1000, 7.2, 416, 5.1, 5.7, 5.9, 12.3, OK
    2, 1, 2, pull_shared, 1000, 7.2, 416, 3.0, 3.4, 3.7, 5.3, OK
    2, 1, 2, update_shared, 1000, 7.2, 416, 3.7, 4.0, 4.3, 7.8, OK
    2, 4, 8, dump_own, 1000, 7.0, 429, 14.9, 42.0, 44.7, 66.2, OK
    2, 4, 8, pull_shared, 1000, 7.0, 429, 18.1, 24.2, 26.4, 29.2, OK
    2, 4, 8, update_shared, 1000, 7.0, 429, 19.0, 25.7, 28.5, 34.2, OK
    2, 16, 32, dump_own, 1024, 7.6, 404, 18.0, 152.8, 189.1, 292.5, OK
    2, 16, 32, pull_shared, 1024, 7.6, 404, 101.4, 115.0, 284.0, 297.9, OK
    2, 16, 32, update_shared, 1024, 7.6, 404, 103.2, 119.3, 286.7, 300.4, OK
    2, 64, 128, dump_own, 1024, 8.5, 361, 796.6, 901.6, 1301.8, 1425.6, OK
    2, 64, 128, pull_shared, 1024, 8.5, 361, 82.7, 353.2, 467.6, 574.5, OK
    2, 64, 128, update_shared, 1024, 8.5, 361, 85.4, 534.0, 577.5, 593.3, OK
    2, 128, 256, dump_own, 1024, 10.4, 297, 2017.5, 2497.4, 3240.0, 3402.3, OK
    2, 128, 256, pull_shared, 1024, 10.4, 297, 12.0, 865.1, 1074.3, 1207.7, OK
    2, 128, 256, update_shared, 1024, 10.4, 297, 12.5, 1185.4, 1237.6, 1245.1, OK
    4, 1, 4, dump_own, 1000, 6.8, 440, 5.4, 5.9, 10.6, 217.7, OK
    4, 1, 4, pull_shared, 1000, 6.8, 440, 8.6, 10.5, 11.3, 221.3, OK
    4, 1, 4, update_shared, 1000, 6.8, 440, 9.2, 11.1, 13.9, 221.4, OK
    4, 4, 16, dump_own, 1008, 7.2, 422, 8.8, 14.3, 63.2, 115.1, OK
    4, 4, 16, pull_shared, 1008, 7.2, 422, 50.3, 55.5, 57.8, 60.5, OK
    4, 4, 16, update_shared, 1008, 7.2, 422, 51.9, 57.3, 61.0, 69.9, OK
    4, 16, 64, dump_own, 1024, 7.5, 408, 11.0, 275.7, 380.0, 493.1, OK
    4, 16, 64, pull_shared, 1024, 7.5, 408, 222.9, 239.4, 243.1, 277.0, OK
    4, 16, 64, update_shared, 1024, 7.5, 408, 226.1, 248.0, 304.2, 313.9, OK
    4, 64, 256, dump_own, 1024, 9.6, 319, 1524.3, 2015.6, 2670.4, 2802.9, OK
    4, 64, 256, pull_shared, 1024, 9.6, 319, 169.2, 832.2, 1026.7, 1127.2, OK
    4, 64, 256, update_shared, 1024, 9.6, 319, 173.6, 1129.9, 1166.6, 1172.6, OK
    4, 128, 512, dump_own, 1536, 18.5, 249, 4362.2, 6842.9, 7748.6, 7909.4, OK
    4, 128, 512, pull_shared, 1536, 18.5, 249, 22.4, 1885.4, 2261.0, 2506.7, OK
    4, 128, 512, update_shared, 1536, 18.5, 249, 22.2, 2457.2, 2527.4, 2536.8, OK
    8, 1, 8, dump_own, 1000, 7.8, 385, 5.7, 6.9, 29.4, 113.7, OK
    8, 1, 8, pull_shared, 1000, 7.8, 385, 26.2, 28.0, 42.2, 136.9, OK
    8, 1, 8, update_shared, 1000, 7.8, 385, 26.9, 29.2, 55.5, 137.9, OK
    8, 4, 32, dump_own, 1024, 7.6, 405, 5.9, 76.4, 147.7, 215.5, OK
    8, 4, 32, pull_shared, 1024, 7.6, 405, 111.7, 119.8, 141.3, 143.2, OK
    8, 4, 32, update_shared, 1024, 7.6, 405, 113.7, 122.9, 142.6, 145.2, OK
    8, 16, 128, dump_own, 1024, 8.4, 364, 67.4, 635.2, 931.0, 1004.0, OK
    8, 16, 128, pull_shared, 1024, 8.4, 364, 358.6, 674.0, 716.4, 732.6, OK
    8, 16, 128, update_shared, 1024, 8.4, 364, 453.9, 677.6, 721.8, 733.3, OK
    8, 64, 512, dump_own, 1536, 17.6, 262, 4196.2, 6256.8, 7159.7, 7303.5, OK
    8, 64, 512, pull_shared, 1536, 17.6, 262, 70.7, 1821.1, 2299.8, 2529.4, OK
    8, 64, 512, update_shared, 1536, 17.6, 262, 71.2, 2469.6, 2532.3, 2547.8, OK
    8, 128, 1024, dump_own, 3072, 41.3, 223, 10367.2, 16202.3, 17669.9, 18038.3, OK
    8, 128, 1024, pull_shared, 3072, 41.3, 223, 28.1, 3487.9, 4570.5, 5215.4, OK
    8, 128, 1024, update_shared, 3072, 41.3, 223, 28.1, 4812.8, 5196.5, 5239.6, OK
    16, 1, 16, dump_own, 1008, 6.2, 490, 4.7, 7.7, 51.4, 88.0, OK
    16, 1, 16, pull_shared, 1008, 6.2, 490, 44.1, 48.1, 61.3, 93.1, OK
    16, 1, 16, update_shared, 1008, 6.2, 490, 45.6, 50.1, 61.9, 95.7, OK
    16, 4, 64, dump_own, 1024, 6.4, 477, 5.5, 199.1, 290.3, 369.5, OK
    16, 4, 64, pull_shared, 1024, 6.4, 477, 193.3, 207.0, 211.1, 235.9, OK
    16, 4, 64, update_shared, 1024, 6.4, 477, 195.6, 211.5, 229.7, 238.1, OK
    16, 16, 256, dump_own, 1024, 7.9, 387, 1056.1, 1710.5, 2100.5, 2206.0, OK
    16, 16, 256, pull_shared, 1024, 7.9, 387, 247.0, 734.2, 912.2, 983.3, OK
    16, 16, 256, update_shared, 1024, 7.9, 387, 279.6, 963.1, 990.0, 996.6, OK
    16, 64, 1024, dump_own, 3072, 35.7, 258, 8539.1, 14173.9, 15308.3, 15595.6, OK
    16, 64, 1024, pull_shared, 3072, 35.7, 258, 10.1, 3220.3, 3924.3, 4496.5, OK
    16, 64, 1024, update_shared, 3072, 35.7, 258, 10.5, 4375.8, 4498.5, 4523.2, OK
    32, 1, 32, dump_own, 1024, 6.0, 508, 4.7, 60.3, 125.0, 176.4, OK
    32, 1, 32, pull_shared, 1024, 6.0, 508, 88.5, 94.8, 96.9, 105.7, OK
    32, 1, 32, update_shared, 1024, 6.0, 508, 89.8, 97.2, 108.8, 116.2, OK
    32, 4, 128, dump_own, 1024, 6.8, 449, 23.3, 547.0, 757.1, 834.5, OK
    32, 4, 128, pull_shared, 1024, 6.8, 449, 335.0, 427.7, 502.0, 583.8, OK
    32, 4, 128, update_shared, 1024, 6.8, 449, 387.2, 567.1, 590.4, 595.9, OK
    32, 16, 512, dump_own, 1536, 15.5, 297, 3629.4, 5518.2, 6349.6, 6474.7, OK
    32, 16, 512, pull_shared, 1536, 15.5, 297, 11.6, 1641.3, 2015.7, 2205.3, OK
    32, 16, 512, update_shared, 1536, 15.5, 297, 13.3, 2152.3, 2212.5, 2228.8, OK
    32, 32, 1024, dump_own, 3072, 35.2, 262, 8796.5, 13619.2, 14756.2, 15022.2, OK
    32, 32, 1024, pull_shared, 3072, 35.2, 262, 10.2, 3045.5, 3870.1, 4436.9, OK
    32, 32, 1024, update_shared, 3072, 35.2, 262, 10.9, 4187.7, 4314.5, 4459.3, OK
    64, 1, 64, dump_own, 1024, 6.6, 466, 5.2, 215.5, 298.3, 389.4, OK
    64, 1, 64, pull_shared, 1024, 6.6, 466, 189.4, 210.0, 219.0, 228.2, OK
    64, 1, 64, update_shared, 1024, 6.6, 466, 194.9, 245.5, 272.4, 279.0, OK
    64, 4, 256, dump_own, 1024, 8.1, 377, 982.0, 1635.9, 2045.5, 2123.1, OK
    64, 4, 256, pull_shared, 1024, 8.1, 377, 314.0, 838.8, 991.2, 1089.1, OK
    64, 4, 256, update_shared, 1024, 8.1, 377, 340.7, 1076.2, 1102.2, 1108.2, OK
    64, 16, 1024, dump_own, 3072, 35.2, 261, 8523.4, 13545.0, 14609.7, 14864.3, OK
    64, 16, 1024, pull_shared, 3072, 35.2, 261, 10.3, 3304.4, 4124.1, 4747.4, OK
    64, 16, 1024, update_shared, 3072, 35.2, 261, 10.9, 4604.3, 4732.7, 4758.4, OK
    128, 1, 128, dump_own, 1024, 7.3, 419, 139.0, 633.4, 938.9, 1012.4, OK
    128, 1, 128, pull_shared, 1024, 7.3, 419, 292.7, 488.0, 520.6, 532.1, OK
    128, 1, 128, update_shared, 1024, 7.3, 419, 389.8, 505.4, 530.2, 535.3, OK
    128, 4, 512, dump_own, 1536, 16.5, 279, 3747.0, 5727.7, 6706.4, 6877.4, OK
    128, 4, 512, pull_shared, 1536, 16.5, 279, 29.8, 1897.5, 2222.0, 2427.6, OK
    128, 4, 512, update_shared, 1536, 16.5, 279, 34.0, 2380.1, 2428.1, 2437.8, OK
    128, 8, 1024, dump_own, 3072, 36.3, 254, 8755.1, 14120.0, 15221.0, 15507.8, OK
    128, 8, 1024, pull_shared, 3072, 36.3, 254, 11.8, 3327.1, 4179.0, 4765.3, OK
    128, 8, 1024, update_shared, 3072, 36.3, 254, 13.1, 4617.8, 4756.2, 4788.5, OK
