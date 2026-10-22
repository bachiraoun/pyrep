Contention benchmark
====================

The benchmark starts many processes, each running many threads, that all work on the same repository.
Every run checks the repository afterwards, and the integrity column reads OK when nothing was lost or corrupted.

- pyrep 4.0.0, python 3.12.10, Darwin 25.3.0 x86_64
- 16 logical processors, open file limit 1048576
- One Repository instance per process; shared record of 2000 items
- Date: 2026-10-21
- ops/s counts every timed operation of the run. The latencies are per operation, in milliseconds.
- The scenario graphs show p50, p95 and max latency, one line for each number of processes, on logarithmic axes. The dashed line marks one second. The tables also give p99.

.. code-block:: bash

    python3 benchmark/bench_ladder.py --markdown results.md


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
    :alt: Latency of 1000 threads split in different ways between processes and threads

The same 1000 threads split in different ways. It shows whether processes or threads are the better way to add load.

.. image:: benchmark_images/comparison.png
    :width: 100%
    :alt: Latency and operations per second of all scenarios at 100 and 1000 threads

All scenarios side by side at 100 and 1000 total threads, with 10 processes.

Runs record 300 to 3000 operations, as the operations column shows. The slowest operation of a bigger run is therefore not directly comparable with the slowest operation of a smaller run.

read_same
---------

.. image:: benchmark_images/read_same.png
    :width: 100%
    :alt: Latency percentiles of the read_same scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, pull_shared, 300, 0.7, 406, 1.2, 1.9, 3.4, 7.6, OK
    1, 10, 10, pull_shared, 300, 0.6, 477, 19.5, 25.4, 26.4, 26.6, OK
    1, 100, 100, pull_shared, 300, 0.6, 518, 179.1, 195.5, 216.5, 223.7, OK
    1, 500, 500, pull_shared, 1500, 4.9, 308, 950.5, 2793.3, 2969.8, 3052.0, OK
    1, 1000, 1000, pull_shared, 3000, 95.3, 31, 2364.4, 89056.5, 90237.0, 90785.1, OK
    10, 1, 10, pull_shared, 300, 0.5, 625, 14.8, 20.4, 23.0, 23.2, OK
    10, 10, 100, pull_shared, 300, 0.6, 542, 169.7, 193.3, 196.4, 197.1, OK
    10, 50, 500, pull_shared, 1500, 2.8, 543, 881.2, 938.5, 983.5, 1011.1, OK
    10, 100, 1000, pull_shared, 3000, 5.8, 516, 1884.6, 2026.3, 2032.9, 2074.9, OK
    50, 1, 50, pull_shared, 300, 0.7, 435, 87.0, 109.7, 217.4, 225.3, OK
    50, 10, 500, pull_shared, 1500, 3.0, 504, 967.6, 1000.4, 1006.6, 1021.7, OK
    50, 20, 1000, pull_shared, 3000, 6.2, 480, 2055.3, 2107.0, 2117.2, 2119.6, OK
    100, 1, 100, pull_shared, 300, 0.9, 325, 199.2, 441.4, 495.2, 502.7, OK
    100, 5, 500, pull_shared, 1500, 3.5, 428, 1067.0, 1264.6, 1296.0, 1309.5, OK
    100, 10, 1000, pull_shared, 3000, 6.4, 472, 1989.6, 2211.8, 2251.4, 2287.2, OK

update_same
-----------

.. image:: benchmark_images/update_same.png
    :width: 100%
    :alt: Latency percentiles of the update_same scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, update_shared, 300, 1.2, 253, 3.0, 3.8, 4.9, 5.3, OK
    1, 10, 10, update_shared, 300, 1.2, 259, 36.8, 44.7, 46.5, 46.8, OK
    1, 100, 100, update_shared, 300, 1.2, 252, 355.6, 388.5, 392.1, 397.6, OK
    1, 500, 500, update_shared, 1500, 7.7, 194, 2065.7, 2927.2, 3325.9, 3673.4, OK
    1, 1000, 1000, update_shared, 3000, 70.2, 43, 4743.4, 56569.7, 59534.7, 61731.4, OK
    10, 1, 10, update_shared, 300, 1.2, 243, 40.0, 43.2, 44.5, 44.7, OK
    10, 10, 100, update_shared, 300, 1.2, 257, 374.9, 410.2, 414.1, 419.4, OK
    10, 50, 500, update_shared, 1500, 5.9, 255, 1928.4, 2104.2, 2105.9, 2107.1, OK
    10, 100, 1000, update_shared, 3000, 12.8, 234, 4192.4, 4652.3, 4656.3, 4660.2, OK
    50, 1, 50, update_shared, 300, 1.5, 201, 229.7, 283.7, 298.3, 299.2, OK
    50, 10, 500, update_shared, 1500, 6.7, 225, 2125.4, 2412.6, 2416.9, 2421.4, OK
    50, 20, 1000, update_shared, 3000, 12.3, 245, 3886.9, 4613.6, 4635.5, 4649.3, OK
    100, 1, 100, update_shared, 300, 1.6, 188, 443.1, 657.4, 697.6, 703.5, OK
    100, 5, 500, update_shared, 1500, 7.2, 209, 2350.4, 2588.3, 2601.3, 2602.3, OK
    100, 10, 1000, update_shared, 3000, 13.5, 223, 4272.3, 5093.4, 5112.2, 5137.0, OK

read_own
--------

.. image:: benchmark_images/read_own.png
    :width: 100%
    :alt: Latency percentiles of the read_own scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, pull_own, 300, 0.4, 719, 1.1, 1.3, 1.5, 2.1, OK
    1, 10, 10, pull_own, 300, 0.3, 883, 10.7, 12.9, 14.2, 15.0, OK
    1, 100, 100, pull_own, 300, 0.3, 1009, 90.4, 112.2, 119.0, 122.9, OK
    1, 500, 500, pull_own, 1500, 33.0, 45, 9789.9, 21994.6, 24390.8, 24894.5, OK
    1, 1000, 1000, pull_own, 3000, 526.4, 6, 169645.8, 236656.8, 245329.2, 280236.1, OK
    10, 1, 10, pull_own, 300, 0.1, 2726, 3.0, 4.1, 4.8, 5.0, OK
    10, 10, 100, pull_own, 300, 0.1, 3275, 26.0, 34.9, 42.3, 45.9, OK
    10, 50, 500, pull_own, 1500, 0.5, 3190, 132.4, 174.5, 204.7, 244.7, OK
    10, 100, 1000, pull_own, 3000, 1.0, 2999, 272.3, 402.0, 450.4, 481.3, OK
    50, 1, 50, pull_own, 300, 0.1, 3156, 13.4, 18.1, 19.4, 19.9, OK
    50, 10, 500, pull_own, 1500, 0.6, 2372, 113.3, 190.8, 236.8, 289.9, OK
    50, 20, 1000, pull_own, 3000, 0.9, 3178, 205.7, 344.7, 389.4, 435.3, OK
    100, 1, 100, pull_own, 300, 0.1, 5360, 14.8, 20.1, 21.4, 21.7, OK
    100, 5, 500, pull_own, 1500, 0.9, 1598, 192.5, 326.5, 333.8, 336.1, OK
    100, 10, 1000, pull_own, 3000, 4.6, 657, 1301.2, 1591.6, 1626.5, 1667.0, OK

update_own
----------

.. image:: benchmark_images/update_own.png
    :width: 100%
    :alt: Latency percentiles of the update_own scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, update_own, 300, 5.4, 56, 15.9, 23.1, 37.5, 38.1, OK
    1, 10, 10, update_own, 300, 3.0, 99, 94.8, 131.2, 142.8, 191.9, OK
    1, 100, 100, update_own, 300, 2.6, 115, 798.3, 951.4, 1045.0, 1071.7, OK
    1, 500, 500, update_own, 1500, 137.3, 11, 48961.5, 82703.4, 100317.5, 123935.4, OK
    1, 1000, 1000, update_own, 3000, 33.1, 91, 7932.1, 16877.4, 17049.0, 19081.4, OK
    10, 1, 10, update_own, 300, 0.4, 759, 12.2, 14.4, 15.9, 16.3, OK
    10, 10, 100, update_own, 300, 0.7, 446, 180.2, 363.6, 382.3, 385.3, OK
    10, 50, 500, update_own, 1500, 13.2, 114, 3465.9, 7106.0, 7145.3, 7170.1, OK
    10, 100, 1000, update_own, 3000, 46.8, 64, 5181.9, 39582.7, 39680.1, 39758.3, OK
    50, 1, 50, update_own, 300, 0.4, 837, 50.6, 78.5, 93.6, 100.4, OK
    50, 10, 500, update_own, 1500, 6.9, 217, 935.0, 5982.4, 6286.7, 6675.2, OK
    50, 20, 1000, update_own, 3000, 32.4, 93, 2179.1, 27778.5, 27869.4, 27925.7, OK
    100, 1, 100, update_own, 300, 0.6, 510, 97.2, 399.0, 423.6, 438.9, OK
    100, 5, 500, update_own, 1500, 11.1, 135, 1396.2, 9717.8, 10151.7, 10625.3, OK
    100, 10, 1000, update_own, 3000, 32.6, 92, 5931.3, 25649.5, 25783.5, 25851.7, OK

create_unique
-------------

.. image:: benchmark_images/create_unique.png
    :width: 100%
    :alt: Latency percentiles of the create_unique scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, dump_own, 300, 2.0, 152, 6.2, 7.0, 7.5, 11.3, OK
    1, 10, 10, dump_own, 300, 2.0, 148, 63.8, 83.2, 111.2, 123.0, OK
    1, 100, 100, dump_own, 300, 2.4, 124, 658.0, 1033.1, 1108.2, 1125.2, OK
    1, 500, 500, dump_own, 1500, 35.9, 42, 4222.9, 25663.5, 26863.2, 27819.0, OK
    1, 1000, 1000, dump_own, 3000, 35.9, 84, 10181.5, 15128.5, 16172.4, 16407.7, OK
    10, 1, 10, dump_own, 300, 1.7, 172, 49.2, 67.9, 236.9, 237.8, OK
    10, 10, 100, dump_own, 300, 1.9, 157, 517.5, 812.4, 874.4, 884.6, OK
    10, 50, 500, dump_own, 1500, 12.3, 122, 3562.5, 5068.5, 5498.8, 5616.7, OK
    10, 100, 1000, dump_own, 3000, 33.3, 90, 9648.5, 14162.6, 15275.8, 15528.9, OK
    50, 1, 50, dump_own, 300, 1.9, 158, 256.0, 416.7, 480.8, 491.8, OK
    50, 10, 500, dump_own, 1500, 12.9, 116, 3758.3, 5420.1, 5849.2, 5956.6, OK
    50, 20, 1000, dump_own, 3000, 31.9, 94, 9302.9, 13687.6, 14826.4, 15101.7, OK
    100, 1, 100, dump_own, 300, 2.6, 115, 652.4, 1031.9, 1108.0, 1120.5, OK
    100, 5, 500, dump_own, 1500, 14.4, 104, 4043.7, 6110.2, 6579.8, 6688.4, OK
    100, 10, 1000, dump_own, 3000, 32.6, 92, 9092.8, 14512.2, 15594.9, 15853.4, OK

mixed
-----

.. image:: benchmark_images/mixed.png
    :width: 100%
    :alt: Latency percentiles of the mixed scenario

.. csv-table::
    :header: "processes", "threads each", "total threads", "operation", "operations", "wall s", "ops/s", "p50 ms", "p95 ms", "p99 ms", "max ms", "integrity"

    1, 1, 1, dump_own, 300, 4.0, 226, 5.0, 6.4, 9.2, 60.6, OK
    1, 1, 1, pull_shared, 300, 4.0, 226, 1.5, 2.0, 2.4, 2.6, OK
    1, 1, 1, update_shared, 300, 4.0, 226, 3.7, 4.7, 5.7, 6.4, OK
    1, 10, 10, dump_own, 300, 2.8, 319, 81.6, 90.1, 93.5, 126.5, OK
    1, 10, 10, pull_shared, 300, 2.8, 319, 2.9, 5.2, 32.4, 40.6, OK
    1, 10, 10, update_shared, 300, 2.8, 319, 4.5, 5.9, 50.4, 54.2, OK
    1, 100, 100, dump_own, 300, 3.3, 276, 732.5, 1192.5, 1413.0, 1438.8, OK
    1, 100, 100, pull_shared, 300, 3.3, 276, 47.5, 365.3, 488.2, 509.6, OK
    1, 100, 100, update_shared, 300, 3.3, 276, 32.6, 499.9, 521.1, 523.1, OK
    1, 500, 500, dump_own, 1500, 26.3, 171, 5389.7, 9563.3, 10343.7, 10531.9, OK
    1, 500, 500, pull_shared, 1500, 26.3, 171, 6.0, 5281.9, 5566.7, 5765.8, OK
    1, 500, 500, update_shared, 1500, 26.3, 171, 8.5, 2733.8, 2898.5, 2930.1, OK
    1, 1000, 1000, dump_own, 3000, 54.8, 164, 12700.7, 21409.5, 23288.9, 23653.4, OK
    1, 1000, 1000, pull_shared, 3000, 54.8, 164, 9.0, 4026.5, 5500.5, 6326.6, OK
    1, 1000, 1000, update_shared, 3000, 54.8, 164, 9.1, 5957.5, 6239.1, 6352.4, OK
    10, 1, 10, dump_own, 300, 2.1, 425, 5.3, 29.2, 47.0, 70.9, OK
    10, 1, 10, pull_shared, 300, 2.1, 425, 30.0, 33.5, 34.5, 34.6, OK
    10, 1, 10, update_shared, 300, 2.1, 425, 32.0, 36.5, 40.1, 41.7, OK
    10, 10, 100, dump_own, 300, 2.4, 372, 318.3, 605.2, 752.7, 764.7, OK
    10, 10, 100, pull_shared, 300, 2.4, 372, 155.1, 322.0, 396.3, 413.7, OK
    10, 10, 100, update_shared, 300, 2.4, 372, 165.0, 411.1, 422.0, 423.9, OK
    10, 50, 500, dump_own, 1500, 16.8, 268, 3739.0, 5900.5, 6706.6, 6846.4, OK
    10, 50, 500, pull_shared, 1500, 16.8, 268, 219.0, 1704.8, 2223.6, 2395.2, OK
    10, 50, 500, update_shared, 1500, 16.8, 268, 229.2, 2323.4, 2392.7, 2411.9, OK
    10, 100, 1000, dump_own, 3000, 42.8, 210, 10693.1, 16666.3, 18054.8, 18414.6, OK
    10, 100, 1000, pull_shared, 3000, 42.8, 210, 39.5, 3691.5, 4568.5, 5186.7, OK
    10, 100, 1000, update_shared, 3000, 42.8, 210, 40.8, 5036.4, 5193.8, 5223.1, OK
    50, 1, 50, dump_own, 300, 2.5, 366, 16.7, 242.8, 341.7, 347.5, OK
    50, 1, 50, pull_shared, 300, 2.5, 366, 145.0, 198.1, 212.3, 223.0, OK
    50, 1, 50, update_shared, 300, 2.5, 366, 182.2, 209.3, 222.2, 229.6, OK
    50, 10, 500, dump_own, 1500, 15.7, 286, 3226.5, 5470.3, 6204.4, 6350.9, OK
    50, 10, 500, pull_shared, 1500, 15.7, 286, 303.3, 1633.3, 2159.7, 2346.4, OK
    50, 10, 500, update_shared, 1500, 15.7, 286, 324.8, 2244.9, 2342.4, 2366.1, OK
    50, 20, 1000, dump_own, 3000, 40.7, 221, 10112.1, 15958.8, 17371.0, 17691.6, OK
    50, 20, 1000, pull_shared, 3000, 40.7, 221, 14.5, 3461.0, 4420.3, 5069.5, OK
    50, 20, 1000, update_shared, 3000, 40.7, 221, 16.7, 4903.2, 5058.9, 5099.3, OK
    100, 1, 100, dump_own, 300, 2.7, 334, 428.1, 604.4, 749.1, 763.0, OK
    100, 1, 100, pull_shared, 300, 2.7, 334, 117.6, 313.1, 376.7, 392.7, OK
    100, 1, 100, update_shared, 300, 2.7, 334, 136.1, 394.1, 405.7, 407.0, OK
    100, 5, 500, dump_own, 1500, 16.7, 270, 3445.7, 5668.3, 6456.3, 6582.6, OK
    100, 5, 500, pull_shared, 1500, 16.7, 270, 352.4, 1745.8, 2261.5, 2469.0, OK
    100, 5, 500, update_shared, 1500, 16.7, 270, 385.8, 2393.4, 2463.5, 2473.1, OK
    100, 10, 1000, dump_own, 3000, 41.7, 216, 9598.1, 16596.2, 17846.3, 18095.5, OK
    100, 10, 1000, pull_shared, 3000, 41.7, 216, 349.2, 3543.8, 4531.5, 5189.0, OK
    100, 10, 1000, update_shared, 3000, 41.7, 216, 381.7, 4970.8, 5169.2, 5217.3, OK
