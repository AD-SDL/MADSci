# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                          |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/madsci\_client/madsci/client/\_\_init\_\_.py                                              |       17 |        0 |    100% |           |
| src/madsci\_client/madsci/client/client\_mixin.py                                             |      183 |       33 |     82% |235, 242, 283, 320, 327, 363, 377, 392-430, 464, 482, 500, 515-521 |
| src/madsci\_client/madsci/client/data\_client.py                                              |      157 |       41 |     74% |85, 109-117, 127-128, 137-148, 214-224, 238, 287-288, 308-309, 371, 388, 404-411, 439-441, 488-498 |
| src/madsci\_client/madsci/client/event\_client.py                                             |      275 |       33 |     88% |65, 93-96, 107-108, 318-321, 329-332, 337, 395, 443-446, 455-458, 463, 488, 493-494, 503-504, 517, 544, 548-552 |
| src/madsci\_client/madsci/client/experiment\_client.py                                        |       59 |        0 |    100% |           |
| src/madsci\_client/madsci/client/lab\_client.py                                               |       35 |       21 |     40% |31-43, 52-58, 67-73, 82-88, 97-103 |
| src/madsci\_client/madsci/client/location\_client.py                                          |       98 |       39 |     60% |45, 62, 76, 86, 104-112, 132-140, 189-198, 218-226, 254-263, 318-327, 374-382, 410-426 |
| src/madsci\_client/madsci/client/node/\_\_init\_\_.py                                         |        4 |        0 |    100% |           |
| src/madsci\_client/madsci/client/node/abstract\_node\_client.py                               |       30 |        4 |     87% |27, 30, 100-101 |
| src/madsci\_client/madsci/client/node/rest\_node\_client.py                                   |      208 |       44 |     79% |63, 146, 282-293, 324-334, 356-391, 418-421, 528, 558, 560, 578 |
| src/madsci\_client/madsci/client/resource\_client.py                                          |      636 |      200 |     69% |102, 127, 149, 176-179, 187, 244-247, 264, 330-334, 350-365, 394, 428-431, 484-491, 497, 514, 526-527, 576, 607, 654-657, 694-696, 738-739, 778-779, 815, 851-852, 888-889, 925-926, 962-963, 994-995, 1026-1031, 1062-1064, 1095-1148, 1200-1210, 1240-1243, 1294-1304, 1325, 1328-1339, 1371-1378, 1402-1405, 1463-1481, 1502-1508, 1557-1583, 1627-1665, 1696-1713, 1797-1801, 1815, 1838-1839, 1847-1851, 1867-1868, 1879, 1916, 1929, 1942-1952 |
| src/madsci\_client/madsci/client/workcell\_client.py                                          |      198 |       45 |     77% |94, 120, 146, 160, 209-213, 219, 245, 249, 273-278, 388-406, 433-461, 503, 511, 519, 524-525, 638, 671 |
| src/madsci\_common/madsci/common/backup\_tools/\_\_init\_\_.py                                |        8 |        0 |    100% |           |
| src/madsci\_common/madsci/common/backup\_tools/backup\_manager.py                             |      172 |       26 |     85% |63-64, 109-111, 133, 149-150, 159-160, 190, 231, 247, 284, 287-288, 304-305, 321-322, 351-356 |
| src/madsci\_common/madsci/common/backup\_tools/backup\_validator.py                           |       90 |       11 |     88% |105-107, 176-178, 256, 269-273, 287 |
| src/madsci\_common/madsci/common/backup\_tools/base\_backup.py                                |       25 |        0 |    100% |           |
| src/madsci\_common/madsci/common/backup\_tools/cli.py                                         |      103 |       20 |     81% |110, 160-170, 174-176, 214-224, 233-234, 239, 243 |
| src/madsci\_common/madsci/common/backup\_tools/mongo\_cli.py                                  |      136 |       17 |     88% |18-19, 59, 150-152, 202-203, 225-226, 239-240, 262-264, 269, 273 |
| src/madsci\_common/madsci/common/backup\_tools/mongodb\_backup.py                             |      280 |       90 |     68% |47, 82-84, 140, 149-168, 204, 209, 249-256, 284, 304-305, 326-328, 336, 358, 363, 368-369, 403, 428-430, 434-482, 515-540, 544-553, 559-560 |
| src/madsci\_common/madsci/common/backup\_tools/postgres\_backup.py                            |      217 |       55 |     75% |12, 128-134, 196, 204-205, 207, 262, 275, 277, 279, 290-296, 303, 330, 356, 360, 373-374, 407-419, 441-442, 456-458, 473-475, 488-494, 506-508 |
| src/madsci\_common/madsci/common/backup\_tools/postgres\_cli.py                               |      104 |        7 |     93% |109-111, 162-163, 179-180 |
| src/madsci\_common/madsci/common/context.py                                                   |       36 |        2 |     94% |    58, 80 |
| src/madsci\_common/madsci/common/data\_manipulation.py                                        |       43 |        0 |    100% |           |
| src/madsci\_common/madsci/common/exceptions.py                                                |       23 |        2 |     91% |     30-31 |
| src/madsci\_common/madsci/common/manager\_base.py                                             |      136 |       35 |     74% |94, 162-166, 216-217, 262-275, 381-414, 438-439 |
| src/madsci\_common/madsci/common/middleware.py                                                |       75 |        2 |     97% |  137, 170 |
| src/madsci\_common/madsci/common/mongodb\_migration\_tool.py                                  |      187 |       82 |     56% |81, 87, 95-107, 111-123, 127-142, 151-154, 170, 183-191, 200-221, 228, 263-267, 294-295, 312-313, 329-365, 371-376, 380-381 |
| src/madsci\_common/madsci/common/mongodb\_version\_checker.py                                 |      146 |       31 |     79% |65, 90, 99, 104-108, 137, 155-166, 254-256, 265, 301-303, 329-330, 338-340, 344, 348-350 |
| src/madsci\_common/madsci/common/nodes.py                                                     |        7 |        0 |    100% |           |
| src/madsci\_common/madsci/common/object\_storage\_helpers.py                                  |      107 |       35 |     67% |45-52, 62-68, 86-92, 130, 199-204, 211-216, 226, 237-243, 294-299, 312-318, 334-355 |
| src/madsci\_common/madsci/common/ownership.py                                                 |       20 |        1 |     95% |        11 |
| src/madsci\_common/madsci/common/types/\_\_init\_\_.py                                        |        2 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/action\_types.py                                       |      383 |       70 |     82% |54, 60, 66, 72, 78, 101, 129, 143, 157, 215-218, 263, 272-276, 336, 340, 346, 426, 507, 524, 528, 531-533, 653, 659, 764-776, 789-807, 897-899, 963, 972-1022 |
| src/madsci\_common/madsci/common/types/admin\_command\_types.py                               |       18 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/auth\_types.py                                         |       38 |        4 |     89% |     94-97 |
| src/madsci\_common/madsci/common/types/backup\_types.py                                       |       22 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/base\_types.py                                         |       58 |       11 |     81% |45, 78, 86-88, 100-102, 111, 149, 162 |
| src/madsci\_common/madsci/common/types/client\_types.py                                       |       34 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/condition\_types.py                                    |       53 |        5 |     91% |     22-26 |
| src/madsci\_common/madsci/common/types/context\_types.py                                      |       11 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/datapoint\_types.py                                    |       90 |       17 |     81% |44-47, 65, 69-71, 77, 79, 100-105, 117, 131, 159, 168 |
| src/madsci\_common/madsci/common/types/event\_types.py                                        |      140 |        9 |     94% |41-44, 262-266 |
| src/madsci\_common/madsci/common/types/experiment\_types.py                                   |       74 |        6 |     92% |119, 136, 138, 140, 142, 144 |
| src/madsci\_common/madsci/common/types/lab\_types.py                                          |       20 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/location\_types.py                                     |       98 |        9 |     91% |30, 32, 34, 36, 41, 46, 51, 98, 170 |
| src/madsci\_common/madsci/common/types/manager\_types.py                                      |       46 |        5 |     89% |     27-31 |
| src/madsci\_common/madsci/common/types/mongodb\_migration\_types.py                           |      214 |      116 |     46% |84, 105, 129-130, 150, 159, 165, 191, 197, 200-203, 206, 218-227, 248-262, 266-271, 293-297, 303-319, 323-333, 338-348, 352-359, 363, 367, 371, 385-441, 458-490 |
| src/madsci\_common/madsci/common/types/node\_types.py                                         |      144 |        7 |     95% |398, 406, 410, 419, 425, 429, 459 |
| src/madsci\_common/madsci/common/types/parameter\_types.py                                    |       37 |        8 |     78% |14, 23, 47, 49, 51, 68, 70, 72 |
| src/madsci\_common/madsci/common/types/resource\_types/\_\_init\_\_.py                        |      296 |       46 |     84% |119, 163, 240, 250, 271, 276, 280, 284, 325, 338, 344, 366, 370, 404, 426, 430, 478-482, 512, 555, 560-561, 572-588, 591-600, 607-609, 640, 655, 684-687, 724-727, 764, 769, 779, 783 |
| src/madsci\_common/madsci/common/types/resource\_types/definitions.py                         |      118 |       10 |     92% |32-34, 219-227, 348, 424 |
| src/madsci\_common/madsci/common/types/resource\_types/resource\_enums.py                     |       37 |        4 |     89% |38, 41, 45, 50 |
| src/madsci\_common/madsci/common/types/resource\_types/server\_types.py                       |       91 |       29 |     68% |30, 32, 34, 36, 38, 40, 42, 44, 53, 55, 57, 59, 61, 63, 72, 74, 91, 107-109, 111, 113, 115, 117, 126, 128, 144, 146, 155-157 |
| src/madsci\_common/madsci/common/types/step\_types.py                                         |       46 |        3 |     93% |121, 162, 164 |
| src/madsci\_common/madsci/common/types/workcell\_types.py                                     |       70 |        7 |     90% |111, 113, 115, 118-121 |
| src/madsci\_common/madsci/common/types/workflow\_types.py                                     |      302 |       64 |     79% |29, 31, 33, 35, 37, 39, 41, 99, 109, 114, 126, 128, 130, 139, 141, 143, 150, 153, 163, 172-186, 194, 294, 298, 327, 355, 365, 367, 376, 378, 380, 382, 384, 386, 388, 390, 392, 394, 396, 398, 400, 402, 404, 408-411, 415-418, 424-427, 470, 480 |
| src/madsci\_common/madsci/common/utils.py                                                     |      307 |       68 |     78% |26-28, 80-81, 91-92, 98, 131-136, 141-143, 265-269, 279-282, 299-342, 362, 368, 374, 376, 378, 431-436, 445, 619, 683-693, 697, 701, 809-823 |
| src/madsci\_common/madsci/common/validators.py                                                |       27 |        0 |    100% |           |
| src/madsci\_common/madsci/common/warnings.py                                                  |        4 |        2 |     50% |       4-7 |
| src/madsci\_common/madsci/common/workflows.py                                                 |       28 |       15 |     46% |14-29, 39-48, 64, 68 |
| src/madsci\_data\_manager/madsci/data\_manager/data\_server.py                                |      130 |       25 |     81% |66-83, 88, 115-116, 124-125, 130-134, 148, 212, 241, 248, 286-287 |
| src/madsci\_event\_manager/madsci/event\_manager/event\_server.py                             |      172 |       93 |     46% |66-86, 98-99, 118-121, 132-139, 156-157, 195-234, 238-242, 248-256, 277-325, 339-379, 384-385 |
| src/madsci\_event\_manager/madsci/event\_manager/events\_csv\_exporter.py                     |      275 |      231 |     16% |29-57, 62-66, 71-72, 77-85, 90-111, 116-144, 149-180, 185-193, 200-233, 240-260, 265-267, 280-282, 297-335, 356-507, 525-638, 645-657, 674-710, 727-753, 770-796 |
| src/madsci\_event\_manager/madsci/event\_manager/notifications.py                             |       52 |        5 |     90% |31-32, 43, 84-85 |
| src/madsci\_event\_manager/madsci/event\_manager/time\_series\_analyzer.py                    |     1014 |      919 |      9% |20-21, 32-57, 64-97, 104-128, 147-163, 175-225, 237-263, 278-307, 312-319, 331-352, 359-376, 381-409, 420, 442-462, 475-506, 524-592, 606-615, 622-639, 654-680, 718, 750-770, 782-810, 822-843, 859-886, 903-981, 999-1043, 1084, 1118-1138, 1145-1160, 1172-1200, 1212-1233, 1244-1249, 1261-1288, 1305-1374, 1386-1404, 1417-1461, 1502, 1531-1589, 1601-1727, 1743-1845, 1865-1886, 1898-1915, 1936-1965, 1984-2012, 2019-2067, 2075-2131, 2145-2158, 2163, 2174-2190, 2195-2196, 2203-2218, 2225-2234, 2241-2250, 2257-2265, 2274-2280, 2287-2321, 2333-2344, 2351-2362, 2369-2406, 2416-2439, 2448-2456, 2466-2477, 2482-2496, 2506-2513, 2520-2522, 2529-2546, 2556, 2568-2572, 2577-2582, 2589-2651, 2672-2708, 2720-2745, 2752-2762, 2769-2776, 2787-2799, 2811-2832, 2842-2863, 2873-2898, 2909-2927, 2932-2934, 2945-2950, 2961-2980, 2992-3001, 3005-3015, 3019-3029 |
| src/madsci\_event\_manager/madsci/event\_manager/utilization\_analyzer.py                     |      769 |      691 |     10% |23-34, 53-109, 124-182, 189-261, 268-282, 289-330, 341-348, 355-370, 386-402, 414-425, 430-436, 442-462, 468-497, 501-624, 636-694, 699-743, 750-821, 826-861, 869-890, 897-910, 916-936, 940, 950-957, 963-964, 971-985, 991-1000, 1004, 1008, 1014-1019, 1025-1035, 1041-1047, 1060-1083, 1092-1096, 1102-1105, 1114-1120, 1127-1185, 1193-1201, 1205-1218, 1224-1261, 1267-1303, 1309-1332, 1340-1366, 1372-1381, 1385-1390, 1396-1410, 1416-1425, 1429-1436, 1442-1460, 1464, 1485-1488, 1492-1493, 1499-1503, 1511-1517, 1522-1579, 1592-1673, 1680-1696, 1700-1717, 1722-1740, 1744-1751, 1755-1760, 1766-1772, 1776-1778, 1782-1785, 1789-1804, 1808-1812, 1816-1818, 1822-1838, 1849-1893, 1897-1931, 1935-1991 |
| src/madsci\_experiment\_application/madsci/experiment\_application/\_\_init\_\_.py            |        2 |        0 |    100% |           |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_application.py |      209 |       23 |     89% |56, 58, 60, 86, 88-101, 103, 105, 131-133, 281, 356-357, 364, 369, 402, 404 |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/experiment\_server.py              |      130 |       27 |     79% |65-85, 90-92, 103, 108, 117-120, 129, 170, 191, 211, 231, 251, 269-270 |
| src/madsci\_location\_manager/madsci/location\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_location\_manager/madsci/location\_manager/location\_server.py                    |      224 |       35 |     84% |83, 116, 140, 154-179, 243-245, 260, 269-273, 362, 428, 507, 550-556, 572-573, 581-582, 589-590 |
| src/madsci\_location\_manager/madsci/location\_manager/location\_state\_handler.py            |       76 |       15 |     80% |72, 84-90, 102-103, 114-115, 127-129, 145-146 |
| src/madsci\_location\_manager/madsci/location\_manager/transfer\_planner.py                   |      175 |        2 |     99% |  282, 315 |
| src/madsci\_node\_module/madsci/node\_module/\_\_init\_\_.py                                  |        4 |        0 |    100% |           |
| src/madsci\_node\_module/madsci/node\_module/abstract\_node\_module.py                        |      525 |      129 |     75% |80, 84, 86, 88, 90, 92, 94, 98, 100, 102, 104, 115, 131, 142, 167-171, 200-202, 211, 232-237, 242-250, 260-267, 295-307, 318-319, 330-340, 362-364, 378-380, 554, 630, 657, 682, 704, 735, 755, 758, 805-806, 835-836, 848-850, 856-857, 907-917, 966, 978, 982, 992-997, 1018, 1021-1033, 1050, 1063, 1069-1070, 1085, 1095-1096, 1102-1103, 1130-1138, 1154, 1170-1174, 1188-1192, 1206-1207, 1221-1222, 1243-1246 |
| src/madsci\_node\_module/madsci/node\_module/helpers.py                                       |      152 |       59 |     61% |42, 69-112, 117-134, 141, 162-167, 224, 243 |
| src/madsci\_node\_module/madsci/node\_module/rest\_node\_module.py                            |      390 |       88 |     77% |64, 68, 70, 72, 82-96, 107-130, 165, 170-181, 220-224, 250, 261-263, 274-288, 303, 311-325, 329, 347-349, 383, 386, 409, 412, 476, 502, 515-520, 532-542, 572, 576, 579-581, 631, 658, 672, 688, 699-700, 798, 886 |
| src/madsci\_resource\_manager/madsci/resource\_manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| src/madsci\_resource\_manager/madsci/resource\_manager/database\_version\_checker.py          |      136 |       21 |     85% |34-36, 139-144, 221-223, 245-247, 264-266, 278-280, 312-314 |
| src/madsci\_resource\_manager/madsci/resource\_manager/migration\_tool.py                     |      353 |      149 |     58% |81-85, 149-156, 161-163, 171, 239-243, 252-253, 261-262, 295-296, 302-322, 326-381, 417-420, 442-445, 449-478, 482-491, 510-512, 522, 549-553, 595-604, 608-638, 642-663, 686-688, 692-693 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_interface.py                 |      643 |      125 |     81% |76, 80, 82, 88-98, 110, 171-173, 305-309, 367, 369, 371, 373, 375, 456, 460-462, 479, 570, 788, 793-794, 825, 843-888, 927-928, 956-960, 989-991, 1023, 1051-1053, 1090-1092, 1119, 1123, 1141-1143, 1155-1156, 1201-1205, 1225, 1281, 1295-1299, 1340-1358, 1373-1375, 1378-1382, 1394-1401, 1444, 1460-1462, 1497-1500, 1511-1513, 1551-1553, 1600 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_server.py                    |      427 |      120 |     72% |86-90, 106-120, 162-163, 203-205, 210-213, 236-238, 249-251, 260-264, 290-292, 345-347, 389-393, 406-408, 415-417, 425-427, 441-443, 451, 455-459, 470-474, 488-490, 533-537, 541, 554-556, 795-800, 815-820, 846-848, 853, 877-879, 884, 909-911, 938-940, 952-964, 976-993, 998-999 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_tables.py                    |      127 |        3 |     98% |196-197, 268 |
| src/madsci\_squid/madsci/squid/\_\_init\_\_.py                                                |        0 |        0 |    100% |           |
| src/madsci\_squid/madsci/squid/lab\_server.py                                                 |       86 |       24 |     72% |55, 82, 85, 88, 91, 94, 97, 114-116, 130-147, 166-167 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/\_\_init\_\_.py                        |        2 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/condition\_checks.py                   |      115 |       52 |     55% |32-41, 52, 54, 61-64, 75-76, 85-86, 98-99, 116-117, 126-127, 139-140, 153-162, 167-177, 186-192, 201-208 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/default\_scheduler.py       |       83 |       23 |     72% |58-63, 88-109, 124-125, 134-135, 150-151 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/scheduler.py                |       16 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/state\_handler.py                      |      194 |       50 |     74% |69, 86, 170, 178-184, 214, 228, 246-260, 270-273, 281-282, 290-293, 306-307, 327, 343, 350-355, 359-361, 367-368, 380, 398-399, 410-415, 423-424, 432 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_actions.py                   |      100 |       14 |     86% |33-39, 105-106, 139-142, 236-237, 258, 291-292 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_engine.py                    |      320 |       97 |     70% |86-149, 168-176, 189, 210, 231, 249, 265, 270-279, 283-286, 307-310, 328, 379-380, 382, 390-394, 419, 461-462, 539-549, 583-592, 610-627 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_server.py                    |      264 |       67 |     75% |86-87, 123-158, 183-184, 231, 243-247, 271-272, 284, 292, 302-305, 313-317, 348, 363, 377, 391, 397, 426-428, 432-437, 462-464, 501-503, 518, 529, 560-565, 572-573 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_utils.py                     |        9 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workflow\_utils.py                     |      199 |       67 |     66% |40-41, 48-58, 72-77, 95, 113, 131, 144, 160, 165-176, 244, 251-252, 268, 279, 300, 305, 313, 330-342, 358-380, 396, 419-426, 433, 438-441, 447-448 |
|                                                                                     **TOTAL** | **13996** | **4545** | **68%** |           |


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