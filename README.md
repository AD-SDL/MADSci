# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                          |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/madsci\_client/madsci/client/\_\_init\_\_.py                                              |       15 |        0 |    100% |           |
| src/madsci\_client/madsci/client/data\_client.py                                              |      156 |       41 |     74% |72, 88-96, 106-107, 116-126, 175-183, 190, 233-234, 253-254, 314, 331, 347-354, 382-384, 431-441 |
| src/madsci\_client/madsci/client/event\_client.py                                             |      266 |       30 |     89% |64, 88-89, 270-273, 281-284, 289, 347, 395-398, 407-410, 415, 440, 445-446, 455-456, 469, 496, 500-504 |
| src/madsci\_client/madsci/client/experiment\_client.py                                        |       57 |        0 |    100% |           |
| src/madsci\_client/madsci/client/location\_client.py                                          |      144 |       66 |     54% |57, 74, 91-93, 103, 113, 131-142, 160-171, 223-235, 255-266, 294-306, 364-376, 424-435, 463-482 |
| src/madsci\_client/madsci/client/node/\_\_init\_\_.py                                         |        4 |        0 |    100% |           |
| src/madsci\_client/madsci/client/node/abstract\_node\_client.py                               |       30 |        4 |     87% |27, 30, 100-101 |
| src/madsci\_client/madsci/client/node/rest\_node\_client.py                                   |      183 |       32 |     83% |60, 116, 216-258, 272, 323, 341, 343, 357 |
| src/madsci\_client/madsci/client/resource\_client.py                                          |      627 |      199 |     68% |100, 125, 147, 174-177, 185, 227-230, 247, 309-313, 326-341, 367, 399-402, 451-458, 464, 477, 488-489, 525, 551, 596-597, 632-634, 674-675, 712-713, 745, 777-778, 810-811, 843-844, 876-877, 906-907, 935-940, 968-970, 1001-1054, 1102-1112, 1138-1141, 1189-1199, 1216, 1219-1230, 1258-1265, 1285-1288, 1331-1350, 1365-1371, 1418-1444, 1486-1524, 1553-1570, 1654-1658, 1672, 1695-1696, 1704-1708, 1724-1725, 1736, 1770, 1783, 1796-1806 |
| src/madsci\_client/madsci/client/workcell\_client.py                                          |      252 |       48 |     81% |122, 151, 179, 194, 243-247, 253, 275, 279, 303-308, 416-437, 464-492, 531, 539, 547, 552-553, 657, 686 |
| src/madsci\_common/madsci/common/context.py                                                   |       20 |        1 |     95% |        11 |
| src/madsci\_common/madsci/common/data\_manipulation.py                                        |       43 |        0 |    100% |           |
| src/madsci\_common/madsci/common/exceptions.py                                                |       23 |        2 |     91% |     30-31 |
| src/madsci\_common/madsci/common/manager\_base.py                                             |       85 |       24 |     72% |120-124, 163-164, 171-184, 246-257, 281-282 |
| src/madsci\_common/madsci/common/nodes.py                                                     |        7 |        0 |    100% |           |
| src/madsci\_common/madsci/common/object\_storage\_helpers.py                                  |      107 |       35 |     67% |45-52, 62-68, 86-92, 130, 199-204, 211-216, 226, 237-243, 294-299, 312-318, 334-355 |
| src/madsci\_common/madsci/common/ownership.py                                                 |       20 |        1 |     95% |        11 |
| src/madsci\_common/madsci/common/types/\_\_init\_\_.py                                        |        0 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/action\_types.py                                       |      376 |       71 |     81% |54, 60, 66, 72, 78, 101, 129, 143, 157, 215-218, 263, 272-276, 336, 340, 346, 426, 507, 524, 528, 531-533, 653, 659, 764-776, 789-807, 913-916, 936, 945-995 |
| src/madsci\_common/madsci/common/types/admin\_command\_types.py                               |       18 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/auth\_types.py                                         |       38 |        4 |     89% |     94-97 |
| src/madsci\_common/madsci/common/types/base\_types.py                                         |       56 |       16 |     71% |45, 78, 86-88, 100-102, 111, 124-126, 138-140, 149 |
| src/madsci\_common/madsci/common/types/condition\_types.py                                    |       53 |        5 |     91% |     22-26 |
| src/madsci\_common/madsci/common/types/context\_types.py                                      |       11 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/datapoint\_types.py                                    |       92 |       17 |     82% |44-47, 65, 69, 71, 77, 79, 100-105, 117, 131, 159, 168 |
| src/madsci\_common/madsci/common/types/event\_types.py                                        |      136 |        9 |     93% |39-42, 240-244 |
| src/madsci\_common/madsci/common/types/experiment\_types.py                                   |       73 |        6 |     92% |108, 125, 127, 129, 131, 133 |
| src/madsci\_common/madsci/common/types/lab\_types.py                                          |       20 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/location\_types.py                                     |      100 |        9 |     91% |30, 32, 34, 36, 41, 46, 51, 98, 170 |
| src/madsci\_common/madsci/common/types/manager\_types.py                                      |       36 |        5 |     86% |     27-31 |
| src/madsci\_common/madsci/common/types/node\_types.py                                         |      138 |        5 |     96% |363, 375, 384, 394, 424 |
| src/madsci\_common/madsci/common/types/parameter\_types.py                                    |       38 |        8 |     79% |14, 23, 47, 49, 51, 68, 70, 72 |
| src/madsci\_common/madsci/common/types/resource\_types/\_\_init\_\_.py                        |      296 |       46 |     84% |119, 163, 240, 250, 271, 276, 280, 284, 325, 338, 344, 366, 370, 404, 426, 430, 478-482, 512, 555, 560-561, 572-588, 591-600, 607-609, 640, 655, 684-687, 724-727, 764, 769, 779, 783 |
| src/madsci\_common/madsci/common/types/resource\_types/definitions.py                         |      118 |       10 |     92% |32-34, 219-227, 348, 424 |
| src/madsci\_common/madsci/common/types/resource\_types/resource\_enums.py                     |       37 |        4 |     89% |38, 41, 45, 50 |
| src/madsci\_common/madsci/common/types/resource\_types/server\_types.py                       |      101 |       29 |     71% |30, 32, 34, 36, 38, 40, 42, 44, 53, 55, 57, 59, 61, 63, 72, 74, 91, 107, 109, 111, 113, 115, 117, 126, 128, 144, 146, 155, 157 |
| src/madsci\_common/madsci/common/types/step\_types.py                                         |       46 |        3 |     93% |118, 159, 161 |
| src/madsci\_common/madsci/common/types/workcell\_types.py                                     |       67 |        7 |     90% |111, 113, 115, 118-121 |
| src/madsci\_common/madsci/common/types/workflow\_types.py                                     |      303 |       64 |     79% |29, 31, 33, 35, 37, 39, 41, 99, 109, 114, 126, 128, 130, 139, 141, 143, 150, 153, 163, 172-186, 194, 294, 298, 327, 355, 365, 367, 376, 378, 380, 382, 384, 386, 388, 390, 392, 394, 396, 398, 400, 402, 404, 408-411, 415-418, 424-427, 470, 480 |
| src/madsci\_common/madsci/common/utils.py                                                     |      212 |       52 |     75% |25, 77-78, 88-89, 95, 128-133, 138-140, 262-266, 276-279, 296-339, 359, 365, 371, 373, 375, 428-433, 442 |
| src/madsci\_common/madsci/common/validators.py                                                |       27 |        0 |    100% |           |
| src/madsci\_common/madsci/common/warnings.py                                                  |        4 |        2 |     50% |       4-7 |
| src/madsci\_common/madsci/common/workflows.py                                                 |       28 |       15 |     46% |14-29, 39-48, 64, 68 |
| src/madsci\_data\_manager/madsci/data\_manager/data\_server.py                                |      125 |       15 |     88% |59, 94-102, 119, 131, 195, 224, 231, 269-270 |
| src/madsci\_event\_manager/madsci/event\_manager/event\_server.py                             |      119 |       45 |     62% |59-60, 79-82, 99, 108-115, 132-133, 171-210, 214-218, 224-232, 237-238 |
| src/madsci\_event\_manager/madsci/event\_manager/events\_csv\_exporter.py                     |      275 |      231 |     16% |29-57, 62-66, 71-72, 77-85, 90-111, 116-144, 149-180, 185-193, 200-233, 240-260, 265-267, 280-282, 297-335, 356-507, 525-638, 645-657, 674-710, 727-753, 770-796 |
| src/madsci\_event\_manager/madsci/event\_manager/notifications.py                             |       52 |        5 |     90% |31-32, 43, 84-85 |
| src/madsci\_event\_manager/madsci/event\_manager/utilization\_analyzer.py                     |      769 |      691 |     10% |23-34, 53-109, 124-182, 189-261, 268-282, 289-330, 341-348, 355-370, 386-402, 414-425, 430-436, 442-462, 468-497, 501-624, 636-694, 699-743, 750-821, 826-861, 869-890, 897-910, 916-936, 940, 950-957, 963-964, 971-985, 991-1000, 1004, 1008, 1014-1019, 1025-1035, 1041-1047, 1060-1083, 1092-1096, 1102-1105, 1114-1120, 1127-1185, 1193-1201, 1205-1218, 1224-1261, 1267-1303, 1309-1332, 1340-1366, 1372-1381, 1385-1390, 1396-1410, 1416-1425, 1429-1436, 1442-1460, 1464, 1485-1488, 1492-1493, 1499-1503, 1511-1517, 1522-1579, 1592-1673, 1680-1696, 1700-1717, 1722-1740, 1744-1751, 1755-1760, 1766-1772, 1776-1778, 1782-1785, 1789-1804, 1808-1812, 1816-1818, 1822-1838, 1849-1893, 1897-1931, 1935-1991 |
| src/madsci\_experiment\_application/madsci/experiment\_application/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_application.py |      211 |       18 |     91% |52, 54, 67, 69, 72, 74, 76, 78, 80, 82, 84, 249, 324-325, 332, 337, 370, 372 |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/experiment\_server.py              |      121 |       18 |     85% |52-54, 65, 70, 79-82, 94, 106, 147, 168, 188, 208, 228, 246-247 |
| src/madsci\_location\_manager/madsci/location\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_location\_manager/madsci/location\_manager/location\_server.py                    |      221 |       35 |     84% |79, 106-107, 130, 154, 168-193, 208, 217-221, 321, 383, 458, 501-507, 523-524, 532-533, 540-541 |
| src/madsci\_location\_manager/madsci/location\_manager/location\_state\_handler.py            |       76 |       15 |     80% |72, 84-90, 102-103, 114-115, 127-129, 145-146 |
| src/madsci\_location\_manager/madsci/location\_manager/transfer\_planner.py                   |      175 |        2 |     99% |  282, 315 |
| src/madsci\_node\_module/madsci/node\_module/\_\_init\_\_.py                                  |        4 |        0 |    100% |           |
| src/madsci\_node\_module/madsci/node\_module/abstract\_node\_module.py                        |      507 |      130 |     74% |78, 82, 84, 86, 88, 90, 92, 96, 98, 100, 102, 113, 129, 140, 165-169, 198-200, 209, 230-235, 240-248, 258-265, 293-305, 316-317, 328-338, 360-362, 376-378, 486, 564, 591, 616, 638, 663, 669, 689, 692, 739-740, 769-770, 782-784, 790-791, 841-851, 900, 912, 916, 926-931, 952, 955-967, 984, 997, 1003-1004, 1019, 1029-1030, 1036-1037, 1064-1072, 1088, 1104-1108, 1122-1126, 1140-1141, 1155-1156, 1177-1180 |
| src/madsci\_node\_module/madsci/node\_module/helpers.py                                       |      152 |       59 |     61% |42, 69-112, 117-134, 141, 162-167, 224, 243 |
| src/madsci\_node\_module/madsci/node\_module/rest\_node\_module.py                            |      348 |       70 |     80% |62, 66, 68, 70, 80-94, 105-119, 143, 148-159, 198-202, 228, 239-241, 252-266, 281, 289-303, 307, 325-327, 361, 364, 387, 390, 454, 480, 538, 565, 579, 595, 606-607, 705, 793 |
| src/madsci\_resource\_manager/madsci/resource\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_interface.py                 |      643 |      125 |     81% |76, 80, 82, 88-98, 110, 171-173, 305-309, 367, 369, 371, 373, 375, 456, 460-462, 479, 570, 788, 793-794, 825, 843-888, 927-928, 956-960, 989-991, 1023, 1051-1053, 1090-1092, 1119, 1123, 1141-1143, 1155-1156, 1201-1205, 1225, 1281, 1295-1299, 1340-1358, 1373-1375, 1378-1382, 1394-1401, 1444, 1460-1462, 1497-1500, 1511-1513, 1551-1553, 1600 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_server.py                    |      400 |       93 |     77% |82-86, 134-135, 175-177, 182-185, 197, 223-225, 236-238, 247-251, 277-279, 332-334, 376-380, 391-393, 400-402, 410-412, 426-428, 436, 440-444, 455-459, 473-475, 521-524, 535-537, 776-781, 796-801, 827-829, 834, 858-860, 865, 890-892, 919-921, 926-927 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_tables.py                    |      121 |        3 |     98% |195-196, 267 |
| src/madsci\_squid/madsci/squid/\_\_init\_\_.py                                                |        0 |        0 |    100% |           |
| src/madsci\_squid/madsci/squid/lab\_server.py                                                 |       91 |       24 |     74% |54, 86, 89, 92, 95, 98, 101, 118-120, 134-151, 175-176 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/\_\_init\_\_.py                        |        2 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/condition\_checks.py                   |      115 |       52 |     55% |32-41, 52, 54, 61-64, 75-76, 85-86, 98-99, 116-117, 126-127, 139-140, 153-162, 167-177, 186-192, 201-208 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/default\_scheduler.py       |       83 |       23 |     72% |52-57, 82-103, 118-119, 128-129, 144-145 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/scheduler.py                |       22 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/state\_handler.py                      |      194 |       50 |     74% |69, 86, 170, 178-184, 214, 228, 246-260, 270-273, 281-282, 290-293, 306-307, 327, 343, 350-355, 359-361, 367-368, 380, 398-399, 410-415, 423-424, 432 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_actions.py                   |      104 |       14 |     87% |33, 35, 37, 39, 105-106, 139-142, 236-237, 258, 291-292 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_engine.py                    |      313 |       91 |     71% |86-137, 156-164, 177, 198, 219, 237, 256-265, 269-272, 293-296, 314, 365-366, 368, 376-380, 405, 447-448, 523-533, 560-569, 575-591 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_server.py                    |      250 |       56 |     78% |71-72, 114-115, 162, 174-178, 191, 213-214, 226, 234, 244-247, 255-259, 290, 305, 319, 333, 339, 368-370, 374-379, 404-406, 443-445, 460, 467-471, 503-508, 515-516 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_utils.py                     |        9 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workflow\_utils.py                     |      198 |       79 |     60% |40-41, 48-58, 72-77, 95, 113, 131, 144, 160, 165-176, 251, 258-259, 276, 287, 307-313, 321, 338-350, 366-388, 400, 403-415, 426-433, 440, 445-448, 454-455 |
|                                                                                     **TOTAL** | **10165** | **2814** | **72%** |           |


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