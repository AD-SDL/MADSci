# MADSci Node Modules

Integrated devices and services available for use in your automated and autonomous
laboratories. Every module below is published in the
[AD-SDL organization](https://github.com/orgs/AD-SDL/repositories?q=module) and was written to
run real experiments, so it is the starting point if you have the same hardware.

Verified against the organization on **22 September 2026**: 36 modules on MADSci, plus 9 older
integrations still on WEI listed at the end.

:::{note}
**A module is a driver, not a machine.** Each entry is a module type. A module drives as many
running nodes as you have units of that instrument, so one `pf400_module` serves every PF400 in
a lab. Counting modules tells you what MADSci can talk to, not how many machines are installed.
See [Understanding Modules](../guides/integrator/01-understanding-modules.md).
:::

## Liquid handling and formulation

| Module | Integrated device(s) |
|---|---|
| [`big_kahuna_module`](https://github.com/AD-SDL/big_kahuna_module) | Unchained Labs Big Kahuna, controlled over SiLA 2. Campaign code in [`AMEWS_big_kahuna_code`](https://github.com/AD-SDL/AMEWS_big_kahuna_code) |
| [`ot2_module`](https://github.com/AD-SDL/ot2_module) | Opentrons OT-2, Flex |
| [`hudson_solo_module`](https://github.com/AD-SDL/hudson_solo_module) | Hudson SOLO |
| [`barty_module`](https://github.com/AD-SDL/barty_module) | Barty the bartending robot, a low cost liquid handler |
| `n9_module` | N9 automated synthesis platform (private repository) |

## Plate handling and storage

| Module | Integrated device(s) |
|---|---|
| [`liconic_module`](https://github.com/AD-SDL/liconic_module) | Liconic STX incubator |
| [`inheco_incubator_module`](https://github.com/AD-SDL/inheco_incubator_module) | INHECO single plate incubator shakers |
| [`a4s_sealer_module`](https://github.com/AD-SDL/a4s_sealer_module) | Azenta A4S automated roll heat sealer |
| [`brooks_xpeel_module`](https://github.com/AD-SDL/brooks_xpeel_module) | Brooks XPeel plate seal remover |
| [`hudson_platecrane_module`](https://github.com/AD-SDL/hudson_platecrane_module) | Hudson PlateCrane EX |
| [`sciclops_module`](https://github.com/AD-SDL/sciclops_module) | Hudson Robotics Sciclops PlateCrane |
| [`hig_centrifuge_module`](https://github.com/AD-SDL/hig_centrifuge_module) | HiG automated plate centrifuge |

## Plate reading and thermal cycling

| Module | Integrated device(s) |
|---|---|
| [`bmg_module`](https://github.com/AD-SDL/bmg_module) | BMG VANTAstar microplate reader |
| [`epoch2_module`](https://github.com/AD-SDL/epoch2_module) | BioTek Epoch2 absorbance reader |
| [`hidex_module`](https://github.com/AD-SDL/hidex_module) | Hidex Sense microplate reader |
| [`biometra_module`](https://github.com/AD-SDL/biometra_module) | Biometra TRobot II thermocycler |

## Materials and elemental analysis

| Module | Integrated device(s) |
|---|---|
| [`pe_icp_module`](https://github.com/AD-SDL/pe_icp_module) | PerkinElmer Syngistix ICP, AVIO 550 Max |
| [`metrohm_m101_module`](https://github.com/AD-SDL/metrohm_m101_module) | Metrohm M101 multichannel galvanostat |
| [`phenom_sem_module`](https://github.com/AD-SDL/phenom_sem_module) | Thermo Fisher Scientific Phenom SEM |
| [`aurora_neware_module`](https://github.com/AD-SDL/aurora_neware_module) | Aurora Neware battery cycler |

## Fabrication

| Module | Integrated device(s) |
|---|---|
| [`prusa_mk4s_module`](https://github.com/AD-SDL/prusa_mk4s_module) | Prusa MK4S 3D printer |

## Robots and motion

| Module | Integrated device(s) |
|---|---|
| [`ur_module`](https://github.com/AD-SDL/ur_module) | Universal Robots arms, end-effectors |
| [`pf400_module`](https://github.com/AD-SDL/pf400_module) | Precise Automation PF400 |
| [`mir_module`](https://github.com/AD-SDL/mir_module) | MiR250 mobile base |
| [`vention_rail_module`](https://github.com/AD-SDL/vention_rail_module) | Vention rack and pinion linear rail |
| [`pal_module`](https://github.com/AD-SDL/pal_module) | PAL System automated sample preparation robot |
| [`openarm_module`](https://github.com/AD-SDL/openarm_module) | OpenArm open source dexterous arm |
| [`vega_module`](https://github.com/AD-SDL/vega_module) | DexMate Vega mobile humanoid |
| [`reachy2_module`](https://github.com/AD-SDL/reachy2_module) | Pollen Robotics Reachy 2 humanoid |
| [`so_arm_module`](https://github.com/AD-SDL/so_arm_module) | SO-ARM101, low cost arm for imitation learning |

## Sensing, control and utility

| Module | Integrated device(s) |
|---|---|
| [`camera_module`](https://github.com/AD-SDL/camera_module) | USB webcams and laboratory cameras |
| [`labjack_module`](https://github.com/AD-SDL/labjack_module) | LabJack DAQ devices |
| [`nanodac_module`](https://github.com/AD-SDL/nanodac_module) | Eurotherm nanodac temperature controller, Modbus over TCP |
| [`sierra_mfc_module`](https://github.com/AD-SDL/sierra_mfc_module) | Sierra Smart-Trak 100 mass flow controller, serial over TCP through a Moxa NPort |
| [`zigbee_module`](https://github.com/AD-SDL/zigbee_module) | Low cost Zigbee sensors |
| [`person_module`](https://github.com/AD-SDL/person_module) | Human input, taken as a step inside a workflow |

## Integrated under WEI, not yet ported

These nine were integrated with [WEI](https://doi.org/10.1039/d3dd00142c), the framework that
preceded MADSci, and carry no MADSci code on any branch. They are real integrations and the
drivers still work, but they need porting before they will run in a MADSci workcell. They are
outside the count of 36.

| Module | Integrated device(s) |
|---|---|
| [`tecan_module`](https://github.com/AD-SDL/tecan_module) | Tecan liquid handler |
| `chemspeed_module` | Chemspeed synthesis platform (private repository) |
| [`biostack_module`](https://github.com/AD-SDL/biostack_module) | BioTek BioStack plate stacker |
| [`kla_module`](https://github.com/AD-SDL/kla_module) | KLA nanoindenter |
| [`henry_module`](https://github.com/AD-SDL/henry_module) | "Henry", a UR5e arm on a MiR250 base driven as one unit |
| [`arduino_module`](https://github.com/AD-SDL/arduino_module) | Arduino microcontroller I/O |
| [`object_detection_module`](https://github.com/AD-SDL/object_detection_module) | Vision based object detection |
| [`rpl_tag_engine_module`](https://github.com/AD-SDL/rpl_tag_engine_module) | AprilTag fiducial marker tracking |
| [`fom_module`](https://github.com/AD-SDL/fom_module) | Remote interfaces to facility owned instruments |

---

Do not have your instrument here? The [Equipment Integrator
Guide](../guides/integrator/README.md) walks through building a module for it, and
`madsci new module` scaffolds one.

If you've got a MADSci Node Module you've developed that you want to see included in this list,
open a PR!
