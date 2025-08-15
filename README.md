# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                          |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/madsci\_client/madsci/client/\_\_init\_\_.py                                              |        7 |        0 |    100% |           |
| src/madsci\_client/madsci/client/data\_client.py                                              |      128 |       31 |     76% |63, 77-85, 95-96, 105-115, 162-170, 177, 220-221, 240-241, 301, 318, 334-341 |
| src/madsci\_client/madsci/client/event\_client.py                                             |      268 |      152 |     43% |62, 89-90, 96-105, 109-129, 133-146, 161-162, 185, 216, 222, 255-297, 325-359, 384-423, 426-432, 435-447, 454-457, 462-478, 492, 497, 501-505 |
| src/madsci\_client/madsci/client/experiment\_client.py                                        |       58 |       40 |     31% |28-35, 41-46, 50-57, 66-77, 83-90, 94-100, 104-109, 113-119, 123-128, 132-137 |
| src/madsci\_client/madsci/client/node/\_\_init\_\_.py                                         |        4 |        0 |    100% |           |
| src/madsci\_client/madsci/client/node/abstract\_node\_client.py                               |       29 |        4 |     86% |26, 29, 95-96 |
| src/madsci\_client/madsci/client/node/rest\_node\_client.py                                   |      115 |       34 |     70% |33, 85, 88-90, 92-93, 120, 131, 133, 136-140, 194, 206-229 |
| src/madsci\_client/madsci/client/resource\_client.py                                          |      593 |      183 |     69% |99, 124, 146, 173-176, 184, 227-230, 247, 276, 305-309, 322-335, 359, 389-392, 441-446, 450, 465, 472-473, 509, 533, 574-575, 610-612, 650-651, 686-687, 717, 747-748, 778-779, 809-810, 840-841, 868-869, 895-900, 926-928, 973-983, 1005-1008, 1050-1060, 1077, 1080-1091, 1115-1122, 1142-1145, 1181-1205, 1218-1224, 1271-1299, 1343-1381, 1410-1427, 1511-1515, 1529, 1552-1553, 1561-1565, 1581-1582, 1593 |
| src/madsci\_client/madsci/client/workcell\_client.py                                          |      240 |      112 |     53% |59, 80-86, 124, 153, 157, 184-195, 216-222, 242-257, 291-308, 339-349, 375-424, 452-481, 567, 588, 780-782, 790-805, 814-821 |
| src/madsci\_common/madsci/common/data\_manipulation.py                                        |       43 |       34 |     21% |15-23, 33-68, 76-81 |
| src/madsci\_common/madsci/common/exceptions.py                                                |       19 |        4 |     79% |21-22, 30-31 |
| src/madsci\_common/madsci/common/object\_storage\_helpers.py                                  |      107 |       35 |     67% |45-52, 62-68, 86-92, 130, 199-204, 211-216, 226, 237-243, 294-299, 312-318, 334-355 |
| src/madsci\_common/madsci/common/ownership.py                                                 |       20 |        1 |     95% |        11 |
| src/madsci\_common/madsci/common/types/\_\_init\_\_.py                                        |        0 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/action\_types.py                                       |      162 |       21 |     87% |49, 55, 61, 72, 89, 117, 131, 145, 231, 235, 237, 307, 372, 380, 390, 393-395, 397-399 |
| src/madsci\_common/madsci/common/types/admin\_command\_types.py                               |       18 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/auth\_types.py                                         |       38 |        4 |     89% |     94-97 |
| src/madsci\_common/madsci/common/types/base\_types.py                                         |       56 |       16 |     71% |45, 78, 86-88, 100-102, 111, 124-126, 138-140, 149 |
| src/madsci\_common/madsci/common/types/condition\_types.py                                    |       53 |        5 |     91% |     22-26 |
| src/madsci\_common/madsci/common/types/context\_types.py                                      |       10 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/datapoint\_types.py                                    |       82 |       13 |     84% |52, 56, 58, 64, 66, 87-92, 104, 118, 146, 155 |
| src/madsci\_common/madsci/common/types/event\_types.py                                        |      133 |        9 |     93% |34-37, 222-226 |
| src/madsci\_common/madsci/common/types/experiment\_types.py                                   |       66 |        6 |     91% |99, 116, 118, 120, 122, 124 |
| src/madsci\_common/madsci/common/types/lab\_types.py                                          |       37 |        5 |     86% |     60-64 |
| src/madsci\_common/madsci/common/types/location\_types.py                                     |       36 |        4 |     89% |19, 21, 23, 99 |
| src/madsci\_common/madsci/common/types/node\_types.py                                         |      138 |        7 |     95% |362, 370, 374, 383, 389, 393, 423 |
| src/madsci\_common/madsci/common/types/resource\_types/\_\_init\_\_.py                        |      296 |       46 |     84% |119, 163, 240, 250, 271, 276, 280, 284, 325, 338, 344, 366, 370, 404, 426, 430, 478-482, 512, 555, 560-561, 572-588, 591-600, 607-609, 640, 655, 684-687, 724-727, 764, 769, 779, 783 |
| src/madsci\_common/madsci/common/types/resource\_types/definitions.py                         |      108 |       10 |     91% |27-29, 166-174, 295, 371 |
| src/madsci\_common/madsci/common/types/resource\_types/resource\_enums.py                     |       37 |        4 |     89% |38, 41, 45, 50 |
| src/madsci\_common/madsci/common/types/resource\_types/server\_types.py                       |       94 |       27 |     71% |30, 32, 34, 36, 38, 40, 42, 44, 53, 55, 57, 59, 61, 63, 72, 74, 91, 107, 109, 111, 113, 115, 117, 126, 128, 144, 146 |
| src/madsci\_common/madsci/common/types/step\_types.py                                         |       29 |        2 |     93% |    82, 84 |
| src/madsci\_common/madsci/common/types/workcell\_types.py                                     |       69 |        7 |     90% |116, 118, 120, 123-126 |
| src/madsci\_common/madsci/common/types/workflow\_types.py                                     |      205 |       62 |     70% |21, 23, 25, 27, 29, 31, 33, 91, 98, 100, 102, 104, 106, 112, 114, 125, 127, 136, 138, 140, 142, 153, 162, 164, 173, 175, 177, 179, 181, 183, 185, 187, 189, 191, 193, 195, 197, 201-204, 208-211, 215-220, 224-232, 239, 249 |
| src/madsci\_common/madsci/common/utils.py                                                     |      193 |      125 |     35% |25, 31, 69-80, 87-97, 102-110, 120-144, 228, 234-238, 251-281, 297-340, 359-379, 387-389, 413-414, 422-427, 429-434, 443, 455 |
| src/madsci\_common/madsci/common/validators.py                                                |       27 |       12 |     56% |14-15, 25-26, 31-35, 48-54 |
| src/madsci\_common/madsci/common/warnings.py                                                  |        4 |        2 |     50% |       4-7 |
| src/madsci\_data\_manager/madsci/data\_manager/data\_server.py                                |      111 |       15 |     86% |46-54, 64, 89, 150, 179, 186, 233-239 |
| src/madsci\_event\_manager/madsci/event\_manager/event\_server.py                             |      159 |       86 |     46% |46-54, 61-62, 83-90, 107-108, 161-200, 222-270, 295-335, 339-343, 349-357, 363-367 |
| src/madsci\_event\_manager/madsci/event\_manager/events\_csv\_exporter.py                     |      275 |      231 |     16% |29-57, 62-66, 71-72, 77-85, 90-111, 116-144, 149-180, 185-193, 200-233, 240-260, 265-267, 280-282, 297-335, 356-507, 525-638, 645-657, 674-710, 727-753, 770-796 |
| src/madsci\_event\_manager/madsci/event\_manager/notifications.py                             |       52 |        5 |     90% |31-32, 43, 84-85 |
| src/madsci\_event\_manager/madsci/event\_manager/time\_series\_analyzer.py                    |     1014 |      919 |      9% |20-21, 32-57, 64-97, 104-128, 147-163, 175-225, 237-263, 278-307, 312-319, 331-352, 359-376, 381-409, 420, 442-462, 475-506, 524-592, 606-615, 622-639, 654-680, 718, 750-770, 782-810, 822-843, 859-886, 903-981, 999-1043, 1084, 1118-1138, 1145-1160, 1172-1200, 1212-1233, 1244-1249, 1261-1288, 1305-1374, 1386-1404, 1417-1461, 1502, 1531-1589, 1601-1727, 1743-1845, 1865-1886, 1898-1915, 1936-1965, 1984-2012, 2019-2067, 2075-2131, 2145-2158, 2163, 2174-2190, 2195-2196, 2203-2218, 2225-2234, 2241-2250, 2257-2265, 2274-2280, 2287-2321, 2333-2344, 2351-2362, 2369-2406, 2416-2439, 2448-2456, 2466-2477, 2482-2496, 2506-2513, 2520-2522, 2529-2546, 2556, 2568-2572, 2577-2582, 2589-2651, 2672-2708, 2720-2745, 2752-2762, 2769-2776, 2787-2799, 2811-2832, 2842-2863, 2873-2898, 2909-2927, 2932-2934, 2945-2950, 2961-2980, 2992-3001, 3005-3015, 3019-3029 |
| src/madsci\_event\_manager/madsci/event\_manager/utilization\_analyzer.py                     |      769 |      691 |     10% |23-34, 53-109, 124-182, 189-261, 268-282, 289-330, 341-348, 355-370, 386-402, 414-425, 430-436, 442-462, 468-497, 501-624, 636-694, 699-743, 750-821, 826-861, 869-890, 897-910, 916-936, 940, 950-957, 963-964, 971-985, 991-1000, 1004, 1008, 1014-1019, 1025-1035, 1041-1047, 1060-1083, 1092-1096, 1102-1105, 1114-1120, 1127-1185, 1193-1201, 1205-1218, 1224-1259, 1265-1299, 1305-1328, 1336-1362, 1368-1377, 1381-1386, 1392-1406, 1412-1421, 1425-1432, 1438-1456, 1460, 1481-1484, 1488-1489, 1495-1499, 1507-1513, 1518-1575, 1588-1669, 1676-1692, 1696-1713, 1718-1736, 1740-1747, 1751-1756, 1762-1768, 1772-1774, 1778-1781, 1785-1800, 1804-1808, 1812-1814, 1818-1834, 1845-1889, 1893-1927, 1931-1987 |
| src/madsci\_experiment\_application/madsci/experiment\_application/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_application.py |      212 |       19 |     91% |52, 54, 67, 69, 72, 74, 76, 78, 80, 82, 84, 86, 253, 324-325, 332, 337, 370, 372 |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/experiment\_server.py              |      110 |       17 |     85% |36-46, 58-59, 76, 115, 136, 156, 176, 196, 223-227 |
| src/madsci\_node\_module/madsci/node\_module/\_\_init\_\_.py                                  |        4 |        0 |    100% |           |
| src/madsci\_node\_module/madsci/node\_module/abstract\_node\_module.py                        |      319 |       90 |     72% |75, 79, 81, 83, 85, 87, 89, 93, 95, 97, 99, 101, 112, 128, 139, 163-167, 196-198, 207, 238-246, 256-263, 286-298, 309-310, 321-331, 353-355, 369-371, 470, 484, 501, 522, 531, 536-537, 547, 551-554, 583-586, 606, 608-610, 613, 620-624, 634, 646-647, 653-654, 681-689, 726-729 |
| src/madsci\_node\_module/madsci/node\_module/helpers.py                                       |       39 |       12 |     69% |37, 60-62, 78-98 |
| src/madsci\_node\_module/madsci/node\_module/rest\_node\_module.py                            |      141 |       50 |     65% |46, 50, 52, 54-58, 70-84, 95-97, 110, 116-121, 135, 148, 177, 183-185, 192-194, 205-226, 238-240, 276 |
| src/madsci\_resource\_manager/madsci/resource\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_interface.py                 |      617 |      122 |     80% |76, 80, 82, 88-98, 110, 171-173, 305-309, 367, 369, 371, 373, 375, 456, 460-462, 479, 570, 788, 793-794, 825, 843-888, 927-928, 956-960, 989-991, 1023, 1051-1053, 1090-1092, 1119, 1123, 1141-1143, 1155-1156, 1225, 1281, 1295-1299, 1340-1358, 1373-1375, 1378-1382, 1394-1401, 1444, 1460-1462, 1497-1500, 1511-1513, 1551-1553 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_server.py                    |      344 |       89 |     74% |53-63, 70-74, 113-116, 125-127, 138-140, 149-153, 179-181, 234-236, 278-282, 293-295, 302-304, 312-314, 328-330, 338, 342-346, 357-361, 375-377, 393-395, 630-635, 650-655, 680-682, 687, 711-713, 718, 741-743, 756-762 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_tables.py                    |      121 |        3 |     98% |195-196, 267 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/condition\_checks.py                   |      101 |       47 |     53% |29-38, 61-62, 69-70, 82-83, 111-112, 119-120, 132-133, 146-155, 160-170, 179-185, 194-201 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/default\_scheduler.py       |       73 |       19 |     74% |50-55, 80-87, 102-103, 111-112, 119-120, 125-126 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/scheduler.py                |       19 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/state\_handler.py                      |      214 |       51 |     76% |72, 92, 97, 111, 191, 199-205, 233, 245-248, 256-257, 265-268, 281-282, 302, 318, 325-330, 334-336, 342-343, 355, 373-374, 385-390, 398-399, 407, 425-426, 436, 444-445, 453 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_engine.py                    |      298 |       88 |     70% |79-128, 147-155, 168, 215, 232-241, 261-264, 282, 300-307, 337-338, 340, 348-352, 377-378, 437, 451, 473-482, 488-506 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_server.py                    |      254 |       65 |     74% |57-63, 94-95, 148-149, 160, 164-167, 176-179, 185-191, 220, 235, 249, 267-270, 292, 331-333, 344-348, 379-384, 400-402, 413-424, 433-437, 455-459 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_utils.py                     |        9 |        7 |     22% |      8-14 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workflow\_utils.py                     |      100 |       39 |     61% |28-29, 38, 45-46, 52-56, 61-62, 68-73, 122, 138, 149-175, 188-202, 233-236, 242-243 |
|                                                                                     **TOTAL** | **8879** | **3682** | **59%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/AD-SDL/MADSci/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AD-SDL/MADSci/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FAD-SDL%2FMADSci%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.