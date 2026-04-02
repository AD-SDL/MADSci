# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/AD-SDL/MADSci/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                                   |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/madsci\_client/madsci/client/\_\_init\_\_.py                                                       |       17 |        0 |    100% |           |
| src/madsci\_client/madsci/client/cli/\_\_init\_\_.py                                                   |       71 |        9 |     87% |16-17, 63, 72, 102-103, 125, 214, 218 |
| src/madsci\_client/madsci/client/cli/commands/\_\_init\_\_.py                                          |        0 |        0 |    100% |           |
| src/madsci\_client/madsci/client/cli/commands/backup.py                                                |       16 |        6 |     62% |     31-44 |
| src/madsci\_client/madsci/client/cli/commands/commands.py                                              |       27 |       23 |     15% |     23-63 |
| src/madsci\_client/madsci/client/cli/commands/completion.py                                            |       15 |        0 |    100% |           |
| src/madsci\_client/madsci/client/cli/commands/config.py                                                |      123 |       18 |     85% |53, 85, 91, 97-100, 200, 216, 233-234, 310-313, 385-388 |
| src/madsci\_client/madsci/client/cli/commands/doctor.py                                                |      167 |       34 |     80% |96, 115, 132, 155-172, 201-219, 237, 248-249, 271-272, 275, 322-323, 410, 416, 423, 425, 430-435, 437-438, 444-445 |
| src/madsci\_client/madsci/client/cli/commands/init.py                                                  |       60 |        7 |     88% |93-94, 106-108, 115-116 |
| src/madsci\_client/madsci/client/cli/commands/logs.py                                                  |      149 |       96 |     36% |42-56, 65-108, 129, 131, 138-145, 156-180, 258-262, 298-346 |
| src/madsci\_client/madsci/client/cli/commands/migrate.py                                               |      213 |       74 |     65% |167, 180-183, 193-250, 267-268, 334, 349-368, 410-413, 423-438 |
| src/madsci\_client/madsci/client/cli/commands/new.py                                                   |      330 |      168 |     49% |18-19, 44-114, 127-137, 170-172, 193-210, 214, 219-222, 226-235, 240-245, 289-322, 380-387, 456-492, 529-548, 609-611, 694-713, 754-776, 819-823 |
| src/madsci\_client/madsci/client/cli/commands/registry.py                                              |      140 |       24 |     83% |146, 160-164, 194-196, 235-248, 303-306 |
| src/madsci\_client/madsci/client/cli/commands/run.py                                                   |       57 |       41 |     28% |59-110, 129-151 |
| src/madsci\_client/madsci/client/cli/commands/start.py                                                 |      268 |      136 |     49% |21-23, 39-41, 46-48, 124-129, 180-183, 195-201, 210-216, 226-258, 263-264, 337, 348, 366-368, 412-444, 478-529, 534-553, 574, 576, 584-592 |
| src/madsci\_client/madsci/client/cli/commands/status.py                                                |      112 |       26 |     77% |59-68, 81-89, 128, 130, 202, 229-246, 256, 261 |
| src/madsci\_client/madsci/client/cli/commands/stop.py                                                  |       89 |       31 |     65% |40-47, 102-115, 158-159, 188-201 |
| src/madsci\_client/madsci/client/cli/commands/tui.py                                                   |       29 |       16 |     45% |32-44, 60, 69-79 |
| src/madsci\_client/madsci/client/cli/commands/validate.py                                              |      109 |       20 |     82% |49, 76-79, 83-85, 93-94, 115, 127, 162-169, 180, 182, 228 |
| src/madsci\_client/madsci/client/cli/commands/version.py                                               |       52 |        4 |     92% |43-44, 151-152 |
| src/madsci\_client/madsci/client/cli/tui/\_\_init\_\_.py                                               |        2 |        0 |    100% |           |
| src/madsci\_client/madsci/client/cli/tui/app.py                                                        |       50 |       21 |     58% |24, 72-76, 80-81, 85-86, 94-99, 107, 111, 127, 131-134 |
| src/madsci\_client/madsci/client/cli/tui/constants.py                                                  |       10 |        2 |     80% |     8, 36 |
| src/madsci\_client/madsci/client/cli/tui/screens/\_\_init\_\_.py                                       |        6 |        0 |    100% |           |
| src/madsci\_client/madsci/client/cli/tui/screens/dashboard.py                                          |      130 |       98 |     25% |27-30, 34, 38-52, 60-62, 66-67, 75-81, 85-97, 112-114, 119-122, 130-131, 137-168, 181-182, 186-198, 205, 209-215, 221-225, 229-230, 234-237 |
| src/madsci\_client/madsci/client/cli/tui/screens/logs.py                                               |      147 |      116 |     21% |44-47, 62-68, 72-86, 90, 94-122, 140-164, 176-217, 222-228, 232-233, 237-240, 244-254, 258-259, 263-267, 272-275, 279-282 |
| src/madsci\_client/madsci/client/cli/tui/screens/new\_wizard.py                                        |      121 |       87 |     28% |44-45, 49-55, 63, 67-84, 139-142, 146-154, 158-160, 164-184, 188-195, 199-212, 221-222, 226-231, 235-244, 248, 252-255, 259-260, 264-266 |
| src/madsci\_client/madsci/client/cli/tui/screens/nodes.py                                              |      166 |      134 |     19% |32-34, 38-43, 47, 51-60, 64-75, 85-94, 99-123, 127-142, 146, 160-162, 166-175, 183-187, 191-193, 200-221, 237-256, 260-268, 274-275, 279-282, 286 |
| src/madsci\_client/madsci/client/cli/tui/screens/status.py                                             |      126 |       99 |     21% |29-31, 35-36, 47-70, 84-86, 90-108, 115-123, 127-133, 139-142, 146-147, 151-171, 181-201, 213-244, 253-263, 269-270, 274 |
| src/madsci\_client/madsci/client/cli/tui/screens/workflows.py                                          |      253 |      209 |     17% |46-49, 61-64, 76-82, 94-98, 112-132, 142-167, 175-177, 181-182, 194-205, 211-213, 222-232, 238-267, 284-287, 291-309, 317-329, 333-340, 347-349, 353-371, 382-394, 406-410, 421-432, 436-451, 459-481, 485-486, 490-493, 497, 501, 505, 509 |
| src/madsci\_client/madsci/client/cli/utils/\_\_init\_\_.py                                             |        2 |        0 |    100% |           |
| src/madsci\_client/madsci/client/cli/utils/output.py                                                   |       43 |       26 |     40% |30, 47-63, 73, 84-86, 97-99, 109, 126, 138 |
| src/madsci\_client/madsci/client/client\_mixin.py                                                      |      203 |       27 |     87% |285, 331, 368, 375, 411, 425, 440-478, 512, 530 |
| src/madsci\_client/madsci/client/data\_client.py                                                       |      158 |       41 |     74% |87, 111-119, 130-131, 142-153, 219-229, 243, 292-293, 313-314, 376, 393, 409-416, 444-446, 498-508 |
| src/madsci\_client/madsci/client/event\_client.py                                                      |      459 |       83 |     82% |52-53, 110, 172-174, 181, 207, 222, 233-235, 272-273, 278, 311-312, 373, 377, 438-445, 461-462, 476-477, 491-492, 506-507, 521-522, 538-539, 549, 559, 577, 597, 607, 619, 651, 656, 659-664, 690-691, 824, 840, 899-902, 910-914, 919, 980, 1028-1031, 1040-1044, 1049, 1089, 1112, 1115-1120, 1122, 1125, 1129-1133 |
| src/madsci\_client/madsci/client/experiment\_client.py                                                 |       59 |        0 |    100% |           |
| src/madsci\_client/madsci/client/lab\_client.py                                                        |       35 |       16 |     54% |37, 56-58, 67-73, 82-88, 97-103 |
| src/madsci\_client/madsci/client/location\_client.py                                                   |      101 |       39 |     61% |46, 72, 86, 96, 114-122, 142-150, 199-208, 228-236, 264-273, 328-337, 384-392, 420-436 |
| src/madsci\_client/madsci/client/node/\_\_init\_\_.py                                                  |        4 |        0 |    100% |           |
| src/madsci\_client/madsci/client/node/abstract\_node\_client.py                                        |       30 |        0 |    100% |           |
| src/madsci\_client/madsci/client/node/rest\_node\_client.py                                            |      211 |       41 |     81% |167, 307-318, 349-359, 381-420, 447-450, 589, 607 |
| src/madsci\_client/madsci/client/otel\_processors.py                                                   |       26 |       18 |     31% |76-87, 108-131 |
| src/madsci\_client/madsci/client/resource\_client.py                                                   |      643 |      204 |     68% |71, 103, 128, 150, 177-180, 188, 246-249, 261, 280, 347-352, 368-383, 412, 446-451, 504-511, 517, 537, 549-550, 599, 631, 679-682, 719-721, 763-764, 803-804, 840, 876-877, 913-914, 950-951, 987-988, 1019-1020, 1051-1056, 1087-1089, 1120-1190, 1242-1252, 1282-1285, 1336-1346, 1367, 1370-1381, 1413-1420, 1444-1447, 1505-1523, 1544-1550, 1603-1645, 1692-1751, 1782-1799, 1883-1887, 1901, 1924-1925, 1933-1937, 1958-1960, 1974-1977, 2016, 2029, 2042-2052 |
| src/madsci\_client/madsci/client/structlog\_config.py                                                  |       46 |       14 |     70% |37-46, 112, 185-189 |
| src/madsci\_client/madsci/client/workcell\_client.py                                                   |      199 |       45 |     77% |104, 134, 164, 178, 229-233, 239, 265, 273, 297-302, 412-430, 460-499, 551, 671, 704 |
| src/madsci\_client/madsci/client/workflow\_display.py                                                  |      261 |      136 |     48% |16, 52-54, 60-63, 70-77, 86-90, 95-96, 102, 104, 133, 143-144, 151-154, 160-163, 179, 185, 217, 219, 221, 250, 255, 281-288, 291, 303-305, 309-313, 317-322, 326-381, 409-439, 443-459, 467-489, 500 |
| src/madsci\_common/madsci/common/backup\_tools/\_\_init\_\_.py                                         |        8 |        0 |    100% |           |
| src/madsci\_common/madsci/common/backup\_tools/backup\_manager.py                                      |      173 |       26 |     85% |68-69, 119-126, 148, 168-169, 183-184, 214, 255, 271, 308, 315-316, 341-342, 367-368, 402-407 |
| src/madsci\_common/madsci/common/backup\_tools/backup\_validator.py                                    |       91 |       11 |     88% |117-125, 194-202, 280, 293-301, 315 |
| src/madsci\_common/madsci/common/backup\_tools/base\_backup.py                                         |       25 |        0 |    100% |           |
| src/madsci\_common/madsci/common/backup\_tools/cli.py                                                  |      106 |       20 |     81% |122, 173-183, 187-189, 228-238, 247-248, 253, 257 |
| src/madsci\_common/madsci/common/backup\_tools/mongo\_cli.py                                           |      139 |       17 |     88% |18-19, 70, 161-163, 213-214, 236-237, 250-251, 273-275, 280, 284 |
| src/madsci\_common/madsci/common/backup\_tools/mongodb\_backup.py                                      |      281 |       90 |     68% |48, 83-85, 151, 160-185, 227, 232, 283-298, 333, 353-354, 385-391, 404, 431, 436, 441-447, 495, 532-540, 544-610, 657-696, 700-717, 728-729 |
| src/madsci\_common/madsci/common/backup\_tools/postgres\_backup.py                                     |      219 |       55 |     75% |12, 129-135, 205, 219-226, 228, 293, 311, 313, 315, 326-332, 339, 366, 399, 403, 421-422, 458-482, 508-513, 530-538, 553-560, 573-579, 600-608 |
| src/madsci\_common/madsci/common/backup\_tools/postgres\_cli.py                                        |      107 |        7 |     93% |118-120, 171-172, 188-189 |
| src/madsci\_common/madsci/common/bundled\_templates/lab/distributed/\{\{lab\_name\}\}/start\_lab.py.j2 |       22 |       14 |     36% |     25-52 |
| src/madsci\_common/madsci/common/bundled\_templates/lab/minimal/\{\{lab\_name\}\}/start\_lab.py.j2     |       22 |       14 |     36% |     25-52 |
| src/madsci\_common/madsci/common/bundled\_templates/lab/standard/\{\{lab\_name\}\}/start\_lab.py.j2    |       22 |       14 |     36% |     25-52 |
| src/madsci\_common/madsci/common/context.py                                                            |      269 |       12 |     96% |22-23, 67, 94, 116, 234, 363, 393, 524, 829, 870, 919 |
| src/madsci\_common/madsci/common/data\_manipulation.py                                                 |       43 |        0 |    100% |           |
| src/madsci\_common/madsci/common/db\_handlers/\_\_init\_\_.py                                          |        5 |        0 |    100% |           |
| src/madsci\_common/madsci/common/db\_handlers/minio\_handler.py                                        |      101 |       11 |     89% |142-151, 196-201, 213, 220-221 |
| src/madsci\_common/madsci/common/db\_handlers/mongo\_handler.py                                        |       57 |        6 |     89% |15, 98-99, 112, 138-139 |
| src/madsci\_common/madsci/common/db\_handlers/postgres\_handler.py                                     |       86 |        5 |     94% |15, 109-110, 212-213 |
| src/madsci\_common/madsci/common/db\_handlers/redis\_handler.py                                        |       78 |        9 |     88% |143-144, 153-155, 159-161, 165-167, 199 |
| src/madsci\_common/madsci/common/deprecation.py                                                        |       61 |       39 |     36% |10-34, 68-92, 135, 188-243 |
| src/madsci\_common/madsci/common/exceptions.py                                                         |       27 |        2 |     93% |     30-31 |
| src/madsci\_common/madsci/common/local\_backends/\_\_init\_\_.py                                       |        0 |        0 |    100% |           |
| src/madsci\_common/madsci/common/local\_backends/inmemory\_collection.py                               |      265 |       41 |     85% |111, 191, 305-308, 327, 331-332, 338, 385, 395, 410-411, 437, 446, 448-450, 453-457, 462-472, 485, 509-514, 527, 529 |
| src/madsci\_common/madsci/common/local\_backends/inmemory\_redis.py                                    |      125 |        1 |     99% |       257 |
| src/madsci\_common/madsci/common/manager\_base.py                                                      |      222 |       60 |     73% |96-98, 132, 175, 190-194, 253-255, 317-325, 330, 355-358, 388, 405-406, 419-421, 427-428, 508, 512-518, 527-528, 639-641, 661-702, 726-727 |
| src/madsci\_common/madsci/common/middleware.py                                                         |      117 |       17 |     85% |19-20, 49, 59-65, 78-88, 214, 247 |
| src/madsci\_common/madsci/common/migration/\_\_init\_\_.py                                             |        3 |        0 |    100% |           |
| src/madsci\_common/madsci/common/migration/converter.py                                                |      128 |       10 |     92% |182-185, 218, 399-400, 413-415 |
| src/madsci\_common/madsci/common/migration/scanner.py                                                  |       92 |        6 |     93% |74, 76, 104, 136-139 |
| src/madsci\_common/madsci/common/mongodb\_migration\_tool.py                                           |      190 |       82 |     57% |41, 85, 99-118, 122-139, 143-163, 172-183, 199, 214-227, 236-262, 269, 322-329, 367-368, 385-386, 405-454, 460-465, 469-470 |
| src/madsci\_common/madsci/common/mongodb\_version\_checker.py                                          |      145 |       31 |     79% |64, 89, 98, 103-110, 139, 160-171, 276-283, 292, 336-343, 369-370, 384-391, 395, 399-401 |
| src/madsci\_common/madsci/common/nodes.py                                                              |        7 |        0 |    100% |           |
| src/madsci\_common/madsci/common/object\_storage\_helpers.py                                           |      107 |       39 |     64% |43-50, 60-66, 84-90, 122-123, 128, 160, 197-202, 209-214, 224, 235-241, 258, 292-297, 310-316, 332-353 |
| src/madsci\_common/madsci/common/openapi\_utils.py                                                     |       43 |       39 |      9% |23-42, 47-68, 85-95 |
| src/madsci\_common/madsci/common/otel/\_\_init\_\_.py                                                  |        6 |        0 |    100% |           |
| src/madsci\_common/madsci/common/otel/bootstrap.py                                                     |      169 |       60 |     64% |47-58, 111, 123-124, 127-132, 200-201, 204-223, 239-248, 251-282, 308, 312-327, 351-367, 380 |
| src/madsci\_common/madsci/common/otel/fastapi\_instrumentation.py                                      |       14 |        4 |     71% | 23, 32-34 |
| src/madsci\_common/madsci/common/otel/propagation.py                                                   |        5 |        0 |    100% |           |
| src/madsci\_common/madsci/common/otel/requests\_instrumentation.py                                     |       13 |        4 |     69% | 22, 31-33 |
| src/madsci\_common/madsci/common/otel/tracing.py                                                       |      141 |        7 |     95% |150-153, 407, 461-462, 522 |
| src/madsci\_common/madsci/common/ownership.py                                                          |      108 |        2 |     98% |  176, 361 |
| src/madsci\_common/madsci/common/registry/\_\_init\_\_.py                                              |        4 |        0 |    100% |           |
| src/madsci\_common/madsci/common/registry/identity\_resolver.py                                        |       88 |       55 |     38% |71-79, 121-125, 129-136, 195-232, 249-267, 279-292, 306-314, 323-324 |
| src/madsci\_common/madsci/common/registry/local\_registry.py                                           |      197 |       44 |     78% |98-100, 204, 239, 258-260, 275-277, 290-303, 323-324, 349, 355, 374, 399, 403-405, 437-440, 443-445, 457-459, 482, 488-489 |
| src/madsci\_common/madsci/common/registry/lock\_manager.py                                             |       84 |       20 |     76% |19, 117, 120, 161-171, 196, 203-207, 238-240 |
| src/madsci\_common/madsci/common/sentry.py                                                             |       78 |        0 |    100% |           |
| src/madsci\_common/madsci/common/settings\_dir.py                                                      |       57 |       12 |     79% |47-64, 85, 128, 182 |
| src/madsci\_common/madsci/common/templates/\_\_init\_\_.py                                             |        3 |        0 |    100% |           |
| src/madsci\_common/madsci/common/templates/engine.py                                                   |      149 |       23 |     85% |145, 200-201, 207, 217, 237-239, 244-250, 256, 271-273, 341, 364, 391-393 |
| src/madsci\_common/madsci/common/templates/registry.py                                                 |      116 |       22 |     81% |98-100, 125, 150, 154, 158, 174-175, 222, 258, 262, 276, 284-302, 318 |
| src/madsci\_common/madsci/common/testing/\_\_init\_\_.py                                               |        5 |        0 |    100% |           |
| src/madsci\_common/madsci/common/testing/runner.py                                                     |      304 |       62 |     80% |164, 171, 178-183, 203, 256-257, 261-264, 273-276, 282-291, 295-304, 409-422, 486, 503, 507, 509-512, 524-546, 602-604, 637-642, 660-661, 675-676, 697, 699, 702-704 |
| src/madsci\_common/madsci/common/testing/template\_validator.py                                        |      197 |      165 |     16% |22, 38-52, 78-79, 102-128, 146-154, 169-210, 228-240, 251-281, 291-297, 301-337, 341-356, 373-398, 402-428 |
| src/madsci\_common/madsci/common/testing/types.py                                                      |      121 |        1 |     99% |       381 |
| src/madsci\_common/madsci/common/testing/validators.py                                                 |      335 |      118 |     65% |34, 56, 144, 152-158, 224-225, 238-240, 276-278, 297, 305-320, 334, 342-360, 374, 382-407, 422, 430-459, 497-498, 504, 507, 523, 525, 547-548, 559, 583, 599-602, 624, 657, 665-702, 717, 721, 729-755, 843-855 |
| src/madsci\_common/madsci/common/types/action\_types.py                                                |      383 |       62 |     84% |101, 129, 143, 157, 215-218, 263, 272-276, 336, 340, 346, 507, 524, 528, 531-533, 764-776, 789-807, 897-899, 963, 972-1022 |
| src/madsci\_common/madsci/common/types/admin\_command\_types.py                                        |       18 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/auth\_types.py                                                  |       38 |        4 |     89% |     94-97 |
| src/madsci\_common/madsci/common/types/backup\_types.py                                                |       22 |       19 |     14% |3-37, 44-88 |
| src/madsci\_common/madsci/common/types/base\_types.py                                                  |      196 |       71 |     64% |5-110, 138-139, 182, 206, 216, 235-236, 269-319, 327, 346, 376, 391, 410, 436, 443, 447, 476, 493, 495, 502, 528, 562, 579-599, 604-605 |
| src/madsci\_common/madsci/common/types/client\_types.py                                                |       34 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/condition\_types.py                                             |       53 |        5 |     91% |     22-26 |
| src/madsci\_common/madsci/common/types/context\_types.py                                               |       11 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/datapoint\_types.py                                             |       92 |        8 |     91% |50-53, 106-111 |
| src/madsci\_common/madsci/common/types/event\_types.py                                                 |      249 |       23 |     91% |34, 50-63, 417-419, 553-560 |
| src/madsci\_common/madsci/common/types/experiment\_types.py                                            |       77 |        2 |     97% |  108, 140 |
| src/madsci\_common/madsci/common/types/lab\_types.py                                                   |       23 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/location\_types.py                                              |      107 |        4 |     96% |46, 51, 103, 175 |
| src/madsci\_common/madsci/common/types/manager\_types.py                                               |       55 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/migration\_types.py                                             |       59 |        1 |     98% |       143 |
| src/madsci\_common/madsci/common/types/mongodb\_migration\_types.py                                    |      214 |      116 |     46% |85, 106, 130-131, 151, 160, 166, 192, 198, 201-204, 207, 219-228, 249-263, 267-272, 294-298, 304-320, 324-334, 339-349, 353-360, 364, 368, 372, 386-442, 459-491 |
| src/madsci\_common/madsci/common/types/node\_types.py                                                  |      183 |        8 |     96% |448, 527, 535, 541, 550, 558, 562, 592 |
| src/madsci\_common/madsci/common/types/parameter\_types.py                                             |       37 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/registry\_types.py                                              |       41 |        1 |     98% |        86 |
| src/madsci\_common/madsci/common/types/resource\_types/\_\_init\_\_.py                                 |      296 |       46 |     84% |119, 163, 240, 250, 271, 276, 280, 284, 325, 338, 344, 366, 370, 404, 426, 430, 478-482, 512, 555, 560-561, 572-588, 591-600, 607-609, 640, 655, 684-687, 724-727, 764, 769, 779, 783 |
| src/madsci\_common/madsci/common/types/resource\_types/definitions.py                                  |      124 |       10 |     92% |34-36, 237-245, 366, 442 |
| src/madsci\_common/madsci/common/types/resource\_types/resource\_enums.py                              |       37 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/resource\_types/server\_types.py                                |       91 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/step\_types.py                                                  |       46 |        1 |     98% |       121 |
| src/madsci\_common/madsci/common/types/template\_types.py                                              |       79 |        0 |    100% |           |
| src/madsci\_common/madsci/common/types/workcell\_types.py                                              |       85 |        9 |     89% |95-97, 158, 160, 162, 165-168 |
| src/madsci\_common/madsci/common/types/workflow\_types.py                                              |      302 |       30 |     90% |99, 163, 172-186, 194, 294, 298, 327, 355, 408-411, 415-418, 424-427, 470, 480 |
| src/madsci\_common/madsci/common/utils.py                                                              |      308 |       63 |     80% |26-28, 80-81, 91-92, 98, 131-136, 141-143, 265-267, 279-280, 299-342, 362, 368, 374, 376, 378, 415-416, 431-436, 631, 697, 703-705, 713, 821-835 |
| src/madsci\_common/madsci/common/validators.py                                                         |       27 |        0 |    100% |           |
| src/madsci\_common/madsci/common/warnings.py                                                           |        4 |        2 |     50% |       4-7 |
| src/madsci\_common/madsci/common/workflows.py                                                          |       28 |       15 |     46% |14-29, 39-48, 64, 68 |
| src/madsci\_data\_manager/madsci/data\_manager/\_\_init\_\_.py                                         |        0 |        0 |    100% |           |
| src/madsci\_data\_manager/madsci/data\_manager/data\_server.py                                         |      164 |       29 |     82% |45, 70-97, 102-107, 120, 142, 150-151, 156-160, 173, 276, 301, 309, 353-354 |
| src/madsci\_event\_manager/madsci/event\_manager/\_\_init\_\_.py                                       |        0 |        0 |    100% |           |
| src/madsci\_event\_manager/madsci/event\_manager/event\_server.py                                      |      357 |      145 |     59% |45, 66, 119, 145-175, 187-194, 224-235, 252-253, 278-281, 308-324, 338-369, 448-465, 634-643, 712-720, 785-792, 809-822, 837-844, 862-906, 910-919, 925-933, 954-1012, 1026-1071, 1076-1077 |
| src/madsci\_event\_manager/madsci/event\_manager/events\_csv\_exporter.py                              |      280 |      234 |     16% |32-74, 79-83, 88-89, 94-102, 107-128, 133-161, 166-197, 202-210, 217-250, 257-277, 282-284, 297-299, 314-352, 373-524, 542-655, 662-674, 691-727, 744-770, 787-813 |
| src/madsci\_event\_manager/madsci/event\_manager/notifications.py                                      |       52 |        5 |     90% |31-35, 46, 91-92 |
| src/madsci\_event\_manager/madsci/event\_manager/time\_series\_analyzer.py                             |     1028 |      933 |      9% |20-21, 32-63, 70-103, 110-134, 153-169, 181-233, 245-273, 288-321, 326-333, 345-366, 373-390, 395-423, 434, 456-476, 489-520, 538-616, 630-639, 646-663, 678-704, 742, 774-794, 806-838, 850-872, 888-917, 934-1012, 1030-1076, 1117, 1151-1171, 1178-1193, 1205-1235, 1247-1273, 1284-1293, 1305-1334, 1351-1425, 1437-1455, 1468-1514, 1555, 1584-1642, 1654-1783, 1799-1902, 1922-1943, 1955-1972, 1993-2022, 2041-2069, 2076-2126, 2134-2190, 2204-2217, 2222, 2233-2249, 2254-2255, 2262-2277, 2284-2293, 2300-2309, 2316-2324, 2333-2339, 2346-2380, 2392-2403, 2410-2421, 2428-2465, 2475-2498, 2507-2515, 2525-2536, 2541-2555, 2565-2572, 2579-2581, 2588-2605, 2615, 2627-2631, 2636-2641, 2648-2710, 2731-2767, 2779-2810, 2817-2829, 2836-2843, 2854-2872, 2882-2903, 2913-2934, 2944-2969, 2980-2998, 3003-3005, 3016-3021, 3032-3051, 3063-3074, 3078-3088, 3092-3102 |
| src/madsci\_event\_manager/madsci/event\_manager/utilization\_analyzer.py                              |      759 |      679 |     11% |23-42, 61-122, 137-202, 209-307, 314-332, 339-385, 396-403, 410-425, 441-457, 469-480, 485-491, 497-517, 523-557, 561-692, 704-775, 780-828, 835-907, 912-952, 960-983, 990-1003, 1009-1029, 1033, 1044-1051, 1057-1058, 1065-1079, 1085-1094, 1098, 1102, 1108-1113, 1119-1129, 1135-1141, 1154-1177, 1186-1190, 1196-1199, 1208-1214, 1221-1288, 1296-1304, 1308-1321, 1326-1342, 1346-1350, 1356-1367, 1373-1387, 1391-1408, 1416-1446, 1452-1461, 1465-1470, 1476-1490, 1496-1505, 1509-1516, 1522-1540, 1544, 1565-1568, 1572-1573, 1579-1583, 1591-1597, 1602-1659, 1672-1759, 1766-1782, 1786-1803, 1808-1826, 1830-1837, 1841-1846, 1852-1858, 1862-1864, 1868-1871, 1875-1890, 1894-1902, 1906-1908, 1912-1928, 1939-1987, 1991-2030, 2034-2095 |
| src/madsci\_experiment\_application/madsci/experiment\_application/\_\_init\_\_.py                     |        7 |        0 |    100% |           |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_application.py          |      207 |       11 |     95% |148-150, 196, 201, 454-455, 462, 467, 500, 502 |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_base.py                 |      181 |       65 |     64% |39, 202, 220, 235, 251-253, 270-280, 314, 364, 366, 392-414, 422-445, 453, 485-508, 527-539, 562, 579, 587-596, 599-608, 648-668, 719-725, 744-753 |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_node.py                 |       41 |       20 |     51% |114-123, 128-148, 152-167, 186-201, 205 |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_notebook.py             |       82 |       14 |     83% |178-186, 215-218, 251-255, 260, 301-303 |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_script.py               |       19 |        4 |     79% |   128-132 |
| src/madsci\_experiment\_application/madsci/experiment\_application/experiment\_tui.py                  |       43 |       19 |     56% |89, 93, 97, 101-102, 107, 121-129, 143-155, 163 |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/\_\_init\_\_.py                             |        0 |        0 |    100% |           |
| src/madsci\_experiment\_manager/madsci/experiment\_manager/experiment\_server.py                       |      140 |       29 |     79% |41, 47, 79-109, 114-123, 146-149, 162, 213, 238, 262, 286, 310, 328-329 |
| src/madsci\_location\_manager/madsci/location\_manager/\_\_init\_\_.py                                 |        0 |        0 |    100% |           |
| src/madsci\_location\_manager/madsci/location\_manager/location\_server.py                             |      204 |       35 |     83% |53, 109, 147, 176, 190-226, 237, 246-250, 334, 401, 485, 524-537, 548-549, 556-557, 564-565 |
| src/madsci\_location\_manager/madsci/location\_manager/location\_state\_handler.py                     |       78 |       22 |     72% |33, 44-47, 58-59, 74, 85-91, 95, 107-108, 119-120, 132-134, 150-151 |
| src/madsci\_location\_manager/madsci/location\_manager/transfer\_planner.py                            |      176 |        2 |     99% |  286, 319 |
| src/madsci\_node\_module/madsci/node\_module/\_\_init\_\_.py                                           |        4 |        0 |    100% |           |
| src/madsci\_node\_module/madsci/node\_module/abstract\_node\_module.py                                 |      542 |       96 |     82% |110, 235-237, 243, 261-262, 278, 309-317, 327-334, 362-374, 385-386, 397-407, 551-552, 565-569, 627, 718, 745, 770, 792, 829, 855, 858, 905-906, 935-936, 948-950, 956-957, 1066, 1078, 1082, 1092-1097, 1118, 1121-1133, 1199-1200, 1215, 1226-1227, 1233-1234, 1271, 1287-1291, 1305-1309, 1323-1324, 1338-1339, 1360-1363 |
| src/madsci\_node\_module/madsci/node\_module/helpers.py                                                |      157 |       62 |     61% |43, 70-113, 118-135, 149, 168-173, 189-192, 242, 261 |
| src/madsci\_node\_module/madsci/node\_module/rest\_node\_module.py                                     |      384 |       78 |     80% |82-96, 107-130, 165, 170-181, 220-224, 250, 261-263, 274-288, 303, 312, 316, 334-336, 370, 373, 396, 399, 463, 489, 502-507, 519-529, 559, 563, 566-568, 618, 645, 659, 675, 686-687, 785, 873 |
| src/madsci\_node\_module/madsci/node\_module/type\_analyzer.py                                         |      153 |       14 |     91% |210, 263-264, 281-282, 298-299, 351-353, 361-363, 370-373 |
| src/madsci\_resource\_manager/madsci/resource\_manager/\_\_init\_\_.py                                 |        1 |        0 |    100% |           |
| src/madsci\_resource\_manager/madsci/resource\_manager/database\_version\_checker.py                   |      136 |       23 |     83% |37-43, 116-117, 148-157, 253-260, 292-299, 316-318, 336-343, 380-387 |
| src/madsci\_resource\_manager/madsci/resource\_manager/migration\_tool.py                              |      352 |      149 |     58% |79-83, 151-158, 167-173, 181, 256-260, 272-273, 289-290, 329-330, 340-368, 377-457, 493-496, 520-526, 534-573, 577-589, 619-625, 635, 671-677, 740-753, 757-797, 801-831, 858-864, 868-869 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_interface.py                          |      657 |      132 |     80% |90-101, 109-123, 135, 200-207, 344-350, 408, 410, 412, 414, 416, 499, 503-505, 522, 565, 618, 841, 846-847, 878, 896-941, 980-981, 1014-1022, 1051-1059, 1091, 1128-1136, 1179-1187, 1214, 1218, 1236-1243, 1255-1256, 1301-1305, 1325, 1399, 1413-1421, 1462-1483, 1498-1500, 1503-1511, 1528-1535, 1575, 1581, 1600-1607, 1642-1649, 1664-1672, 1710-1718, 1765 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_server.py                             |      434 |      124 |     71% |71, 110-123, 143-164, 200-201, 234-236, 241-244, 268-275, 287-294, 303-313, 350-358, 426-433, 481-491, 504-511, 518-525, 536-543, 557-565, 573, 577-587, 598-608, 622-630, 673-681, 685, 703-712, 1018-1033, 1048-1063, 1089-1099, 1104, 1128-1137, 1142, 1167-1175, 1202-1210, 1222-1239, 1251-1285, 1290-1291 |
| src/madsci\_resource\_manager/madsci/resource\_manager/resource\_tables.py                             |      127 |        3 |     98% |196-197, 268 |
| src/madsci\_squid/madsci/squid/\_\_init\_\_.py                                                         |        0 |        0 |    100% |           |
| src/madsci\_squid/madsci/squid/lab\_server.py                                                          |       89 |       27 |     70% |52, 79, 82, 85, 88, 91, 94, 116-119, 137-163, 185-186 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/\_\_init\_\_.py                                 |        2 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/condition\_checks.py                            |      115 |       52 |     55% |32-41, 52, 54, 61-64, 75-76, 85-86, 98-99, 116-117, 126-127, 139-140, 153-162, 167-177, 186-192, 201-208 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/default\_scheduler.py                |       84 |       23 |     73% |59-67, 92-113, 128-129, 138-139, 154-155 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/schedulers/scheduler.py                         |       16 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/state\_handler.py                               |      199 |       57 |     71% |50, 56, 70-73, 83, 102-103, 124, 203, 211-217, 245, 257, 275-289, 299-302, 310-311, 319-322, 335-336, 356, 372, 379-384, 388-390, 396-397, 409, 427-428, 438, 446-447, 455, 459-460 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_actions.py                            |      100 |       10 |     90% |105-106, 139-142, 236-237, 258, 291-292 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_engine.py                             |      355 |       93 |     74% |102-179, 198-211, 229, 267, 288, 333, 355, 369-382, 386-389, 412-421, 454, 512-519, 521-527, 529, 542-552, 580, 617-620, 664-665, 747-757, 826, 858-880 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_server.py                             |      277 |       79 |     71% |79, 85, 143-202, 229-230, 272, 284-288, 312-313, 324, 334-337, 345-356, 388-392, 410-415, 432-436, 452, 454, 460, 489-490, 494-503, 528-529, 566-567, 582, 593, 630-640, 647-648 |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workcell\_utils.py                              |       12 |        0 |    100% |           |
| src/madsci\_workcell\_manager/madsci/workcell\_manager/workflow\_utils.py                              |      223 |       74 |     67% |42-43, 50-60, 74-79, 97, 115, 133, 146, 162, 167-178, 246, 253-254, 270, 291, 312, 317, 325, 342-354, 370-392, 408, 431-438, 445, 461-463, 481-487, 497-499 |
| **TOTAL**                                                                                              | **22671** | **7308** | **68%** |           |


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