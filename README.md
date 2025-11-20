# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                          |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/madsci\_client/madsci/client/\_\_init\_\_.py                                              |       15 |        0 |    100% |           |
| src/madsci\_client/madsci/client/data\_client.py                                              |      155 |       41 |     74% |72, 88-96, 106-107, 116-126, 175-183, 190, 233-234, 253-254, 314, 331, 347-354, 382-384, 431-441 |
| src/madsci\_client/madsci/client/event\_client.py                                             |      266 |       30 |     89% |64, 88-89, 270-273, 281-284, 289, 347, 395-398, 407-410, 415, 440, 445-446, 455-456, 469, 496, 500-504 |
| src/madsci\_client/madsci/client/experiment\_client.py                                        |       56 |        0 |    100% |           |
| src/madsci\_client/madsci/client/lab\_client.py                                               |       32 |       19 |     41% |28-34, 40-43, 47-50, 54-57, 61-64 |
| src/madsci\_client/madsci/client/location\_client.py                                          |      143 |       66 |     54% |57, 74, 91-93, 103, 113, 131-142, 160-171, 223-235, 255-266, 294-306, 364-376, 424-435, 463-482 |
| src/madsci\_client/madsci/client/node/\_\_init\_\_.py                                         |        4 |        0 |    100% |           |
| src/madsci\_client/madsci/client/node/abstract\_node\_client.py                               |       30 |        4 |     87% |27, 30, 100-101 |
| src/madsci\_client/madsci/client/node/rest\_node\_client.py                                   |      205 |       44 |     79% |62, 118, 219-230, 250-260, 270-305, 320-323, 394, 412, 414, 428 |
| src/madsci\_client/madsci/client/resource\_client.py                                          |      631 |      198 |     69% |101, 126, 148, 175-178, 186, 228-231, 248, 310-314, 327-342, 368, 400-403, 452-459, 465, 478, 489-490, 526, 552, 597-598, 633-635, 675-676, 713-714, 746, 778-779, 811-812, 844-845, 877-878, 907-908, 936-941, 969-971, 1002-1055, 1103-1113, 1139-1142, 1190-1200, 1217, 1220-1231, 1259-1266, 1286-1289, 1345-1363, 1378-1384, 1431-1457, 1499-1537, 1566-1583, 1667-1671, 1685, 1708-1709, 1717-1721, 1737-1738, 1749, 1783, 1796, 1809-1819 |
| src/madsci\_client/madsci/client/workcell\_client.py                                          |      251 |       48 |     81% |122, 151, 179, 194, 243-247, 253, 275, 279, 303-308, 416-437, 464-492, 531, 539, 547, 552-553, 657, 686 |
| src/madsci\_common/madsci/common/context.py                                                   |       22 |        2 |     91% |    11, 44 |
| src/madsci\_common/madsci/common/data\_manipulation.py                                        |       43 |        0 |    100% |           |
| src/madsci\_common/madsci/common/exceptions.py                                                |       23 |        2 |     91% |     30-31 |
| src/madsci\_common/madsci/common/manager\_base.py                                             |      112 |       25 |     78% |89, 157-161, 200-201, 246-259, 321-332, 356-357 |
| src/madsci\_common/madsci/common/nodes.py                                                     |        7 |        0 |    100% |           |
| src/madsci\_common/madsci/common/object\_storage\_helpers.py                                  |      107 |       35 |     67% |45-52, 62-68, 86-92, 130, 199-204, 211-216, 226, 237-243, 294-299, 312-318, 334-355 |
| src/madsci\_common/madsci/common/ownership.py                                                 |       20 |        1 |     95% |        11 |
| src/madsci\_common/madsci/common/types/\_\_init\_\_.py                                        |        0 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/action\_types.py                                       |      383 |       70 |     82% |54, 60, 66, 72, 78, 101, 129, 143, 157, 215-218, 263, 272-276, 336, 340, 346, 426, 507, 524, 528, 531-533, 653, 659, 764-776, 789-807, 897-899, 963, 972-1022 |
| src/madsci\_common/madsci/common/types/admin\_command\_types.py                               |       18 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/auth\_types.py                                         |       38 |        4 |     89% |     94-97 |
| src/madsci\_common/madsci/common/types/base\_types.py                                         |       58 |       17 |     71% |45, 78, 86-88, 100-102, 111, 124-126, 138-140, 149, 162 |
| src/madsci\_common/madsci/common/types/condition\_types.py                                    |       53 |        5 |     91% |     22-26 |
| src/madsci\_common/madsci/common/types/context\_types.py                                      |       11 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/datapoint\_types.py                                    |       88 |       17 |     81% |44-47, 65, 69-71, 77, 79, 100-105, 117, 131, 159, 168 |
| src/madsci\_common/madsci/common/types/event\_types.py                                        |      136 |        9 |     93% |39-42, 240-244 |
| src/madsci\_common/madsci/common/types/experiment\_types.py                                   |       72 |        6 |     92% |108, 125, 127, 129, 131, 133 |
| src/madsci\_common/madsci/common/types/lab\_types.py                                          |       20 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/location\_types.py                                     |       98 |        9 |     91% |30, 32, 34, 36, 41, 46, 51, 98, 170 |
| src/madsci\_common/madsci/common/types/manager\_types.py                                      |       36 |        5 |     86% |     27-31 |
| src/madsci\_common/madsci/common/types/node\_types.py                                         |      138 |        7 |     95% |363, 371, 375, 384, 390, 394, 424 |
| src/madsci\_common/madsci/common/types/parameter\_types.py                                    |       37 |        8 |     78% |14, 23, 47, 49, 51, 68, 70, 72 |
| src/madsci\_common/madsci/common/types/resource\_types/\_\_init\_\_.py                        |      296 |       46 |     84% |119, 163, 240, 250, 271, 276, 280, 284, 325, 338, 344, 366, 370, 404, 426, 430, 478-482, 512, 555, 560-561, 572-588, 591-600, 607-609, 640, 655, 684-687, 724-727, 764, 769, 779, 783 |
| src/madsci\_common/madsci/common/types/resource\_types/definitions.py                         |      118 |       10 |     92% |32-34, 219-227, 348, 424 |
| src/madsci\_common/madsci/common/types/resource\_types/resource\_enums.py                     |       37 |        4 |     89% |38, 41, 45, 50 |
| src/madsci\_common/madsci/common/types/resource\_types/server\_types.py                       |       91 |       29 |     68% |30, 32, 34, 36, 38, 40, 42, 44, 53, 55, 57, 59, 61, 63, 72, 74, 91, 107-109, 111, 113, 115, 117, 126, 128, 144, 146, 155-157 |
| src/madsci\_common/madsci/common/types/step\_types.py                                         |       46 |        3 |     93% |121, 162, 164 |
| src/madsci\_common/madsci/common/types/workcell\_types.py                                     |       67 |        7 |     90% |111, 113, 115, 118-121 |
| src/madsci\_common/madsci/common/types/workflow\_types.py                                     |      302 |       64 |     79% |29, 31, 33, 35, 37, 39, 41, 99, 109, 114, 126, 128, 130, 139, 141, 143, 150, 153, 163, 172-186, 194, 294, 298, 327, 355, 365, 367, 376, 378, 380, 382, 384, 386, 388, 390, 392, 394, 396, 398, 400, 402, 404, 408-411, 415-418, 424-427, 470, 480 |
| src/madsci\_common/madsci/common/utils.py                                                     |      212 |       52 |     75% |25, 77-78, 88-89, 95, 128-133, 138-140, 262-266, 276-279, 296-339, 359, 365, 371, 373, 375, 428-433, 442 |
| src/madsci\_common/madsci/common/validators.py                                                |       27 |        0 |    100% |           |
| src/madsci\_common/madsci/common/warnings.py                                                  |        4 |        2 |     50% |       4-7 |
| src/madsci\_common/madsci/common/workflows.py                                                 |       28 |       15 |     46% |14-29, 39-48, 64, 68 |
| src/madsci\_data\_manager/madsci/data\_manager/data\_server.py                                |      116 |       14 |     88% |59, 94-102, 116, 180, 209, 216, 254-255 |
| src/madsci\_event\_manager/madsci/event\_manager/event\_server.py                             |      154 |       83 |     46% |60-61, 80-83, 94-101, 118-119, 157-196, 200-204, 210-218, 239-287, 301-341, 346-347 |
| src/madsci\_event\_manager/madsci/event\_manager/events\_csv\_exporter.py                     |      275 |      231 |     16% |29-57, 62-66, 71-72, 77-85, 90-111, 116-144, 149-180, 185-193, 200-233, 240-260, 265-267, 280-282, 297-335, 356-507, 525-638, 645-657, 674-710, 727-753, 770-796 |
| src/madsci\_event\_manager/madsci/event\_manager/notifications.py                             |       52 |        5 |     90% |31-32, 43, 84-85 |
| src/madsci\_event\_manager/madsci/event\_manager/time\_series\_analyzer.py                    |     1014 |      919 |      9% |20-21, 32-57, 64-97, 104-128, 147-163, 175-225, 237-263, 278-307, 312-319, 331-352, 359-376, 381-409, 420, 442-462, 475-506, 524-592, 606-615, 622-639, 654-680, 718, 750-770, 782-810, 822-843, 859-886, 903-981, 999-1043, 1084, 1118-1138, 1145-1160, 1172-1200, 1212-1233, 1244-1249, 1261-1288, 1305-1374, 1386-1404, 1417-1461, 1502, 1531-1589, 1601-1727, 1743-1845, 1865-1886, 1898-1915, 1936-1965, 1984-2012, 2019-2067, 2075-2131, 2145-2158, 2163, 2174-2190, 2195-2196, 2203-2218, 2225-2234, 2241-2250, 2257-2265, 2274-2280, 2287-2321, 2333-2344, 2351-2362, 2369-2406, 2416-2439, 2448-2456, 2466-2477, 2482-2496, 2506-2513, 2520-2522, 2529-2546, 2556, 2568-2572, 2577-2582, 2589-2651, 2672-2708, 2720-2745, 2752-2762, 2769-2776, 2787-2799, 2811-2832, 2842-2863, 2873-2898, 2909-2927, 2932-2934, 2945-2950, 2961-2980, 2992-3001, 3005-3015, 3019-3029 |
| src/madsci\_event\_manager/madsci/event\_manager/utilization\_analyzer.py                     |      769 |      691 |     10% |23-34, 53-109, 124-182, 189-261, 268-282, 289-330, 341-348, 355-370, 386-402, 414-425, 430-436, 442-462, 468-497, 501-624, 636-694, 699-743, 750-821, 826-861, 869-890, 897-910, 916-936, 940, 950-957, 963-964, 971-985, 991-1000, 1004, 1008, 1014-1019, 1025-1035, 1041-1047, 1060-1083, 1092-1096, 1102-1105, 1114-1120, 1127-1185, 1193-1201, 1205-1218, 1224-1261, 1267-1303, 1309-1332, 1340-1366, 1372-1381, 1385-1390, 1396-1410, 1416-1425, 1429-1436, 1442-1460, 1464, 1485-1488, 1492-1493, 1499-1503, 1511-1517, 1522-1579, 1592-1673, 1680-1696, 1700-1717, 1722-1740, 1744-1751, 1755-1760, 1766-1772, 1776-1778, 1782-1785, 1789-1804, 1808-1812, 1816-1818, 1822-1838, 1849-1893, 1897-1931, 1935-1991 |
| src/madsci\_experiment\_application/madsci/experiment\_application/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_application.py |      214 |       22 |     90% |54, 56, 58, 71, 73-86, 88, 90, 105-106, 257, 332-333, 340, 345, 378, 380 |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/experiment\_server.py              |      112 |       17 |     85% |52-54, 65, 70, 79-82, 91, 132, 153, 173, 193, 213, 231-232 |
| src/madsci\_location\_manager/madsci/location\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_location\_manager/madsci/location\_manager/location\_server.py                    |      202 |       33 |     84% |79, 112, 136, 150-175, 190, 199-203, 288, 350, 425, 468-474, 490-491, 499-500, 507-508 |
| src/madsci\_location\_manager/madsci/location\_manager/location\_state\_handler.py            |       76 |       15 |     80% |72, 84-90, 102-103, 114-115, 127-129, 145-146 |
| src/madsci\_location\_manager/madsci/location\_manager/transfer\_planner.py                   |      175 |        2 |     99% |  282, 315 |
| src/madsci\_node\_module/madsci/node\_module/\_\_init\_\_.py                                  |        4 |        0 |    100% |           |
| src/madsci\_node\_module/madsci/node\_module/abstract\_node\_module.py                        |      524 |      129 |     75% |78, 82, 84, 86, 88, 90, 92, 96, 98, 100, 102, 113, 129, 140, 165-169, 198-200, 209, 230-235, 240-248, 258-265, 293-305, 316-317, 328-338, 360-362, 376-378, 541, 617, 644, 669, 691, 722, 742, 745, 792-793, 822-823, 835-837, 843-844, 894-904, 953, 965, 969, 979-984, 1005, 1008-1020, 1037, 1050, 1056-1057, 1072, 1082-1083, 1089-1090, 1117-1125, 1141, 1157-1161, 1175-1179, 1193-1194, 1208-1209, 1230-1233 |
| src/madsci\_node\_module/madsci/node\_module/helpers.py                                       |      152 |       59 |     61% |42, 69-112, 117-134, 141, 162-167, 224, 243 |
| src/madsci\_node\_module/madsci/node\_module/rest\_node\_module.py                            |      370 |       81 |     78% |62, 66, 68, 70, 80-94, 105-119, 144, 149-160, 199-203, 229, 240-242, 253-267, 282, 290-304, 308, 326-328, 362, 365, 388, 391, 455, 481, 494-499, 511-521, 584, 611, 625, 641, 652-653, 751, 839 |
| src/madsci\_resource\_manager/madsci/resource\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_interface.py                 |      643 |      125 |     81% |76, 80, 82, 88-98, 110, 171-173, 305-309, 367, 369, 371, 373, 375, 456, 460-462, 479, 570, 788, 793-794, 825, 843-888, 927-928, 956-960, 989-991, 1023, 1051-1053, 1090-1092, 1119, 1123, 1141-1143, 1155-1156, 1201-1205, 1225, 1281, 1295-1299, 1340-1358, 1373-1375, 1378-1382, 1394-1401, 1444, 1460-1462, 1497-1500, 1511-1513, 1551-1553, 1600 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_server.py                    |      394 |       94 |     76% |82-86, 134-135, 175-177, 182-185, 208-210, 221-223, 232-236, 262-264, 317-319, 361-365, 378-380, 387-389, 397-399, 413-415, 423, 427-431, 442-446, 460-462, 505-509, 513, 526-528, 767-772, 787-792, 818-820, 825, 849-851, 856, 881-883, 910-912, 917-918 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_tables.py                    |      121 |        3 |     98% |195-196, 267 |
| src/madsci\_squid/madsci/squid/\_\_init\_\_.py                                                |        0 |        0 |    100% |           |
| src/madsci\_squid/madsci/squid/lab\_server.py                                                 |       86 |       24 |     72% |55, 82, 85, 88, 91, 94, 97, 114-116, 130-147, 166-167 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/\_\_init\_\_.py                        |        2 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/condition\_checks.py                   |      115 |       52 |     55% |32-41, 52, 54, 61-64, 75-76, 85-86, 98-99, 116-117, 126-127, 139-140, 153-162, 167-177, 186-192, 201-208 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/default\_scheduler.py       |       83 |       23 |     72% |58-63, 88-109, 124-125, 134-135, 150-151 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/scheduler.py                |       16 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/state\_handler.py                      |      194 |       50 |     74% |69, 86, 170, 178-184, 214, 228, 246-260, 270-273, 281-282, 290-293, 306-307, 327, 343, 350-355, 359-361, 367-368, 380, 398-399, 410-415, 423-424, 432 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_actions.py                   |      100 |       14 |     86% |33-39, 105-106, 139-142, 236-237, 258, 291-292 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_engine.py                    |      315 |       92 |     71% |86-137, 156-164, 177, 198, 219, 237, 253, 258-267, 271-274, 295-298, 316, 367-368, 370, 378-382, 407, 449-450, 525-535, 562-571, 577-593 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_server.py                    |      243 |       53 |     78% |71-72, 114-115, 162, 174-178, 202-203, 215, 223, 233-236, 244-248, 279, 294, 308, 322, 328, 357-359, 363-368, 393-395, 432-434, 449, 460, 491-496, 503-504 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_utils.py                     |        9 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workflow\_utils.py                     |      199 |       67 |     66% |40-41, 48-58, 72-77, 95, 113, 131, 144, 160, 165-176, 244, 251-252, 268, 279, 300, 305, 313, 330-342, 358-380, 396, 419-426, 433, 438-441, 447-448 |
|                                                                                     **TOTAL** | **11267** | **3802** | **66%** |           |


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