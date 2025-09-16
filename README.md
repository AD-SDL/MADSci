# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                          |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/madsci\_client/madsci/client/\_\_init\_\_.py                                              |       14 |        0 |    100% |           |
| src/madsci\_client/madsci/client/data\_client.py                                              |      126 |       31 |     75% |71, 87-95, 105-106, 115-125, 174-182, 189, 232-233, 252-253, 313, 330, 346-353 |
| src/madsci\_client/madsci/client/event\_client.py                                             |      266 |       30 |     89% |64, 88-89, 270-273, 281-284, 289, 347, 395-398, 407-410, 415, 440, 445-446, 455-456, 469, 496, 500-504 |
| src/madsci\_client/madsci/client/experiment\_client.py                                        |       57 |        0 |    100% |           |
| src/madsci\_client/madsci/client/node/\_\_init\_\_.py                                         |        4 |        0 |    100% |           |
| src/madsci\_client/madsci/client/node/abstract\_node\_client.py                               |       29 |        4 |     86% |26, 29, 95-96 |
| src/madsci\_client/madsci/client/node/rest\_node\_client.py                                   |      115 |        2 |     98% |   33, 131 |
| src/madsci\_client/madsci/client/resource\_client.py                                          |      590 |      183 |     69% |99, 124, 146, 173-176, 184, 226-229, 246, 277, 308-312, 325-340, 366, 398-401, 450-457, 463, 478, 489-490, 526, 552, 597-598, 633-635, 675-676, 713-714, 746, 778-779, 811-812, 844-845, 877-878, 907-908, 936-941, 969-971, 1020-1030, 1056-1059, 1107-1117, 1134, 1137-1148, 1176-1183, 1203-1206, 1244-1268, 1283-1289, 1336-1364, 1406-1444, 1473-1490, 1574-1578, 1592, 1615-1616, 1624-1628, 1644-1645, 1656 |
| src/madsci\_client/madsci/client/workcell\_client.py                                          |      287 |       48 |     83% |123, 152, 180, 195, 244-248, 254, 276, 280, 304-309, 417-438, 465-493, 532, 540, 548, 553-554, 658, 687 |
| src/madsci\_common/madsci/common/context.py                                                   |       20 |        1 |     95% |        11 |
| src/madsci\_common/madsci/common/data\_manipulation.py                                        |       43 |        0 |    100% |           |
| src/madsci\_common/madsci/common/exceptions.py                                                |       19 |        2 |     89% |     30-31 |
| src/madsci\_common/madsci/common/manager\_base.py                                             |       86 |       17 |     80% |120-124, 165-166, 174, 180, 184, 248-259, 283-284 |
| src/madsci\_common/madsci/common/object\_storage\_helpers.py                                  |      107 |       35 |     67% |45-52, 62-68, 86-92, 130, 199-204, 211-216, 226, 237-243, 294-299, 312-318, 334-355 |
| src/madsci\_common/madsci/common/ownership.py                                                 |       20 |        1 |     95% |        11 |
| src/madsci\_common/madsci/common/types/\_\_init\_\_.py                                        |        0 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/action\_types.py                                       |      164 |       19 |     88% |49, 55, 61, 72, 89, 117, 131, 145, 231, 237, 307, 372, 390, 393-395, 397-399 |
| src/madsci\_common/madsci/common/types/admin\_command\_types.py                               |       18 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/auth\_types.py                                         |       38 |        4 |     89% |     94-97 |
| src/madsci\_common/madsci/common/types/base\_types.py                                         |       56 |       10 |     82% |45, 78, 86-88, 100-102, 111, 149 |
| src/madsci\_common/madsci/common/types/condition\_types.py                                    |       53 |        5 |     91% |     22-26 |
| src/madsci\_common/madsci/common/types/context\_types.py                                      |       10 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/datapoint\_types.py                                    |       92 |       17 |     82% |44-47, 65, 69, 71, 77, 79, 100-105, 117, 131, 159, 168 |
| src/madsci\_common/madsci/common/types/event\_types.py                                        |      136 |        9 |     93% |39-42, 240-244 |
| src/madsci\_common/madsci/common/types/experiment\_types.py                                   |       73 |        6 |     92% |108, 125, 127, 129, 131, 133 |
| src/madsci\_common/madsci/common/types/lab\_types.py                                          |       20 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/location\_types.py                                     |       36 |        4 |     89% |19, 21, 23, 99 |
| src/madsci\_common/madsci/common/types/manager\_types.py                                      |       35 |        5 |     86% |     26-30 |
| src/madsci\_common/madsci/common/types/node\_types.py                                         |      138 |        7 |     95% |362, 370, 374, 383, 389, 393, 423 |
| src/madsci\_common/madsci/common/types/parameter\_types.py                                    |       48 |       12 |     75% |14, 23, 47, 49, 51, 53, 59, 75, 77, 79, 83, 89 |
| src/madsci\_common/madsci/common/types/resource\_types/\_\_init\_\_.py                        |      296 |       46 |     84% |119, 163, 240, 250, 271, 276, 280, 284, 325, 338, 344, 366, 370, 404, 426, 430, 478-482, 512, 555, 560-561, 572-588, 591-600, 607-609, 640, 655, 684-687, 724-727, 764, 769, 779, 783 |
| src/madsci\_common/madsci/common/types/resource\_types/definitions.py                         |      111 |       10 |     91% |31-33, 184-192, 313, 389 |
| src/madsci\_common/madsci/common/types/resource\_types/resource\_enums.py                     |       37 |        4 |     89% |38, 41, 45, 50 |
| src/madsci\_common/madsci/common/types/resource\_types/server\_types.py                       |       94 |       27 |     71% |30, 32, 34, 36, 38, 40, 42, 44, 53, 55, 57, 59, 61, 63, 72, 74, 91, 107, 109, 111, 113, 115, 117, 126, 128, 144, 146 |
| src/madsci\_common/madsci/common/types/step\_types.py                                         |       46 |        3 |     93% |111, 152, 154 |
| src/madsci\_common/madsci/common/types/workcell\_types.py                                     |       74 |       10 |     86% |69-71, 129, 131, 133, 136-139 |
| src/madsci\_common/madsci/common/types/workflow\_types.py                                     |      309 |       82 |     73% |7, 11-18, 43, 45, 47, 49, 51, 53, 55, 113, 123, 128, 140, 142, 144, 153, 155, 157, 161, 164, 175, 180, 189-203, 211, 311, 315, 341, 369, 379, 381, 390, 392, 394, 396, 398, 400, 402, 404, 406, 408, 410, 412, 414, 416, 418, 422-425, 429-432, 436-441, 445-453, 460, 470 |
| src/madsci\_common/madsci/common/utils.py                                                     |      192 |       52 |     73% |25, 77-78, 88-89, 95, 128-133, 138-140, 262-266, 276-279, 296-339, 359, 365, 371, 373, 375, 428-433, 442 |
| src/madsci\_common/madsci/common/validators.py                                                |       27 |        0 |    100% |           |
| src/madsci\_common/madsci/common/warnings.py                                                  |        4 |        2 |     50% |       4-7 |
| src/madsci\_common/madsci/common/workflows.py                                                 |       28 |       15 |     46% |14-29, 39-48, 64, 68 |
| src/madsci\_data\_manager/madsci/data\_manager/data\_server.py                                |      125 |       15 |     88% |59, 94-102, 119, 131, 195, 224, 231, 269-270 |
| src/madsci\_event\_manager/madsci/event\_manager/event\_server.py                             |      119 |       45 |     62% |59-60, 79-82, 99, 108-115, 132-133, 171-210, 214-218, 224-232, 237-238 |
| src/madsci\_event\_manager/madsci/event\_manager/events\_csv\_exporter.py                     |      275 |      231 |     16% |29-57, 62-66, 71-72, 77-85, 90-111, 116-144, 149-180, 185-193, 200-233, 240-260, 265-267, 280-282, 297-335, 356-507, 525-638, 645-657, 674-710, 727-753, 770-796 |
| src/madsci\_event\_manager/madsci/event\_manager/notifications.py                             |       52 |        5 |     90% |31-32, 43, 84-85 |
| src/madsci\_event\_manager/madsci/event\_manager/utilization\_analyzer.py                     |      769 |      691 |     10% |23-34, 53-109, 124-182, 189-261, 268-282, 289-330, 341-348, 355-370, 386-402, 414-425, 430-436, 442-462, 468-497, 501-624, 636-694, 699-743, 750-821, 826-861, 869-890, 897-910, 916-936, 940, 950-957, 963-964, 971-985, 991-1000, 1004, 1008, 1014-1019, 1025-1035, 1041-1047, 1060-1083, 1092-1096, 1102-1105, 1114-1120, 1127-1185, 1193-1201, 1205-1218, 1224-1261, 1267-1303, 1309-1332, 1340-1366, 1372-1381, 1385-1390, 1396-1410, 1416-1425, 1429-1436, 1442-1460, 1464, 1485-1488, 1492-1493, 1499-1503, 1511-1517, 1522-1579, 1592-1673, 1680-1696, 1700-1717, 1722-1740, 1744-1751, 1755-1760, 1766-1772, 1776-1778, 1782-1785, 1789-1804, 1808-1812, 1816-1818, 1822-1838, 1849-1893, 1897-1931, 1935-1991 |
| src/madsci\_experiment\_application/madsci/experiment\_application/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_application.py |      208 |       18 |     91% |51, 53, 66, 68, 71, 73, 75, 77, 79, 81, 83, 247, 318-319, 326, 331, 364, 366 |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/experiment\_server.py              |      121 |       18 |     85% |52-54, 65, 70, 79-82, 94, 106, 147, 168, 188, 208, 228, 246-247 |
| src/madsci\_node\_module/madsci/node\_module/\_\_init\_\_.py                                  |        4 |        0 |    100% |           |
| src/madsci\_node\_module/madsci/node\_module/abstract\_node\_module.py                        |      318 |       90 |     72% |74, 78, 80, 82, 84, 86, 88, 92, 94, 96, 98, 109, 125, 136, 161-165, 194-196, 205, 236-244, 254-261, 284-296, 307-308, 319-329, 351-353, 367-369, 470, 484, 501, 522, 531, 536-537, 547, 551-554, 583-586, 606, 608-610, 613, 620-624, 634, 639, 649-650, 656-657, 684-692, 729-732 |
| src/madsci\_node\_module/madsci/node\_module/helpers.py                                       |      108 |       61 |     44% |44, 71-114, 123-135, 146, 148, 150, 156-158, 174-194 |
| src/madsci\_node\_module/madsci/node\_module/rest\_node\_module.py                            |      141 |       50 |     65% |46, 50, 52, 54-58, 70-84, 95-97, 110, 116-121, 135, 148, 177, 183-185, 192-194, 205-226, 238-240, 276 |
| src/madsci\_resource\_manager/madsci/resource\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_interface.py                 |      617 |      122 |     80% |76, 80, 82, 88-98, 110, 171-173, 305-309, 367, 369, 371, 373, 375, 456, 460-462, 479, 570, 788, 793-794, 825, 843-888, 927-928, 956-960, 989-991, 1023, 1051-1053, 1090-1092, 1119, 1123, 1141-1143, 1155-1156, 1225, 1281, 1295-1299, 1340-1358, 1373-1375, 1378-1382, 1394-1401, 1444, 1460-1462, 1497-1500, 1511-1513, 1551-1553 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_server.py                    |      366 |       88 |     76% |78-82, 129-131, 136-139, 151, 177-180, 189-191, 202-204, 213-217, 243-245, 298-300, 342-346, 357-359, 366-368, 376-378, 392-394, 402, 406-410, 421-425, 439-441, 457-459, 698-703, 718-723, 749-751, 756, 780-782, 787, 812-814, 819-820 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_tables.py                    |      121 |        3 |     98% |195-196, 267 |
| src/madsci\_squid/madsci/squid/\_\_init\_\_.py                                                |        0 |        0 |    100% |           |
| src/madsci\_squid/madsci/squid/lab\_server.py                                                 |       89 |       23 |     74% |54, 86, 89, 92, 95, 98, 115-117, 131-148, 172-173 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/\_\_init\_\_.py                        |        2 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/condition\_checks.py                   |      101 |       47 |     53% |29-38, 61-62, 69-70, 82-83, 111-112, 119-120, 132-133, 146-155, 160-170, 179-185, 194-201 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/default\_scheduler.py       |       76 |       19 |     75% |52-57, 82-89, 104-105, 114-115, 122-123, 130-131 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/scheduler.py                |       19 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/state\_handler.py                      |      229 |       56 |     76% |73, 93, 98, 112, 192, 200-206, 236, 250, 268-282, 292-295, 303-304, 312-315, 328-329, 349, 365, 372-377, 381-383, 389-390, 402, 420-421, 432-437, 445-446, 454, 472-473, 483, 500 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_actions.py                   |        6 |        2 |     67% |     10-11 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_engine.py                    |      310 |       85 |     73% |80-131, 150-158, 171, 193, 220, 237-246, 250-253, 273-276, 294, 342-343, 345, 353-357, 479, 493, 515-524, 530-548 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_server.py                    |      294 |       65 |     78% |71-72, 113-114, 163, 175-179, 193, 215-216, 228, 236, 246-249, 255-261, 290, 305, 319, 333, 339, 368-370, 375-380, 405-407, 444-446, 461, 468-472, 503-508, 528, 550, 562-566, 583-584 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_utils.py                     |        9 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workflow\_utils.py                     |      194 |       79 |     59% |39-40, 47-57, 67-72, 90, 106, 121, 134, 150, 155-166, 234, 241-242, 258, 269, 287-293, 301, 318-330, 341-367, 379, 382-394, 405-412, 419, 424-427, 433-434 |
|                                                                                     **TOTAL** | **8593** | **2516** | **71%** |           |


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