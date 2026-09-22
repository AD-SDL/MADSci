# Integrated Equipment

Every instrument, robot and controller below has a reusable MADSci **node module** published in
the [AD-SDL organization](https://github.com/orgs/AD-SDL/repositories?q=module). These modules
were written to run real experiments in Argonne's RAPID laboratories and at collaborating
sites, and they are the starting point if you have the same hardware.

Verified against the organization on **22 September 2026**: 36 instrument modules on MADSci,
plus 9 older integrations still on WEI listed at the end.

:::{note}
**A module is a driver, not a machine.** Each entry is a module type. A module drives as many
running nodes as you have units of that instrument, so one `pf400_module` serves every PF400
in a lab. Counting modules tells you what MADSci can talk to, not how many machines are
installed. See [Understanding Modules](guides/integrator/01-understanding-modules.md).
:::

Do not have your instrument here? The [Equipment Integrator
Guide](guides/integrator/README.md) walks through building a module for it, and
`madsci new module` scaffolds one.

## Liquid handling and formulation

| Instrument | Vendor / detail | Module |
|---|---|---|
| Big Kahuna | Unchained Labs, controlled over SiLA 2 | [`big_kahuna_module`](https://github.com/AD-SDL/big_kahuna_module) |
| OT-2 | Opentrons | [`ot2_module`](https://github.com/AD-SDL/ot2_module) |
| SOLO | Hudson Robotics | [`hudson_solo_module`](https://github.com/AD-SDL/hudson_solo_module) |
| Barty | Low cost liquid handler built in house | [`barty_module`](https://github.com/AD-SDL/barty_module) |
| N9 | Automated synthesis platform (private repository) | `n9_module` |

## Plate handling and storage

| Instrument | Vendor / detail | Module |
|---|---|---|
| Incubator | Liconic | [`liconic_module`](https://github.com/AD-SDL/liconic_module) |
| Single plate incubator shakers | INHECO | [`inheco_incubator_module`](https://github.com/AD-SDL/inheco_incubator_module) |
| Automated roll heat sealer | Azenta, formerly a4S | [`a4s_sealer_module`](https://github.com/AD-SDL/a4s_sealer_module) |
| XPeel | Brooks, plate seal removal | [`brooks_xpeel_module`](https://github.com/AD-SDL/brooks_xpeel_module) |
| PlateCrane | Hudson Robotics | [`hudson_platecrane_module`](https://github.com/AD-SDL/hudson_platecrane_module) |
| Sciclops | Hudson Robotics | [`sciclops_module`](https://github.com/AD-SDL/sciclops_module) |
| HiG centrifuge | Automated plate centrifuge | [`hig_centrifuge_module`](https://github.com/AD-SDL/hig_centrifuge_module) |

## Plate reading and thermal cycling

| Instrument | Vendor / detail | Module |
|---|---|---|
| Microplate reader | BMG Labtech | [`bmg_module`](https://github.com/AD-SDL/bmg_module) |
| Epoch2 | BioTek, absorbance reader | [`epoch2_module`](https://github.com/AD-SDL/epoch2_module) |
| Plate reader | Hidex | [`hidex_module`](https://github.com/AD-SDL/hidex_module) |
| Thermal cycler | Biometra | [`biometra_module`](https://github.com/AD-SDL/biometra_module) |

## Materials and elemental analysis

| Instrument | Vendor / detail | Module |
|---|---|---|
| ICP spectrometer | PerkinElmer, Syngistix on an AVIO 550 Max | [`pe_icp_module`](https://github.com/AD-SDL/pe_icp_module) |
| M101 multichannel galvanostat | Metrohm | [`metrohm_m101_module`](https://github.com/AD-SDL/metrohm_m101_module) |
| Phenom SEM | Thermo Fisher Scientific | [`phenom_sem_module`](https://github.com/AD-SDL/phenom_sem_module) |
| Battery cycler | Aurora Neware | [`aurora_neware_module`](https://github.com/AD-SDL/aurora_neware_module) |

## Fabrication

| Instrument | Vendor / detail | Module |
|---|---|---|
| MK4S 3D printer | Prusa | [`prusa_mk4s_module`](https://github.com/AD-SDL/prusa_mk4s_module) |

## Robots and motion

| Instrument | Vendor / detail | Module |
|---|---|---|
| UR5e arms | Universal Robots | [`ur_module`](https://github.com/AD-SDL/ur_module) |
| PF400 arm | PreciseFlex | [`pf400_module`](https://github.com/AD-SDL/pf400_module) |
| MiR250 mobile base | Mobile Industrial Robots | [`mir_module`](https://github.com/AD-SDL/mir_module) |
| Linear rail | Vention | [`vention_rail_module`](https://github.com/AD-SDL/vention_rail_module) |
| PAL3 | PAL Systems, sample handling robot | [`pal_module`](https://github.com/AD-SDL/pal_module) |
| OpenArm | Open source dexterous arm | [`openarm_module`](https://github.com/AD-SDL/openarm_module) |
| Vega | DexMate, mobile humanoid | [`vega_module`](https://github.com/AD-SDL/vega_module) |
| Reachy 2 | Pollen Robotics, humanoid | [`reachy2_module`](https://github.com/AD-SDL/reachy2_module) |
| SO-ARM101 | Low cost arm for imitation learning | [`so_arm_module`](https://github.com/AD-SDL/so_arm_module) |

## Sensing, control and utility

| Instrument | Vendor / detail | Module |
|---|---|---|
| Cameras | Imaging across the self driving laboratories | [`camera_module`](https://github.com/AD-SDL/camera_module) |
| LabJack DAQ | Analog and digital sensor acquisition | [`labjack_module`](https://github.com/AD-SDL/labjack_module) |
| nanodac temperature controller | Eurotherm, Modbus over TCP | [`nanodac_module`](https://github.com/AD-SDL/nanodac_module) |
| Smart-Trak 100 mass flow controller | Sierra, serial over TCP through a Moxa NPort | [`sierra_mfc_module`](https://github.com/AD-SDL/sierra_mfc_module) |
| Zigbee sensors | Wireless environmental sensing | [`zigbee_module`](https://github.com/AD-SDL/zigbee_module) |
| Human in the loop | Takes operator input as a step inside a workflow | [`person_module`](https://github.com/AD-SDL/person_module) |

## Integrated under WEI, not yet ported

These nine were integrated with [WEI](https://doi.org/10.1039/d3dd00142c), the framework that
preceded MADSci, and carry no MADSci code on any branch. They are real integrations and the
drivers still work, but they need porting before they will run in a MADSci workcell. They are
outside the count of 36.

| Instrument | Vendor / detail | Module |
|---|---|---|
| Liquid handler | Tecan | [`tecan_module`](https://github.com/AD-SDL/tecan_module) |
| Synthesis platform | Chemspeed (private repository) | `chemspeed_module` |
| BioStack | BioTek, plate stacker | [`biostack_module`](https://github.com/AD-SDL/biostack_module) |
| Nanoindenter | KLA | [`kla_module`](https://github.com/AD-SDL/kla_module) |
| Henry | UR5e arm on a MiR250 base, driven as one unit | [`henry_module`](https://github.com/AD-SDL/henry_module) |
| Arduino I/O | General purpose microcontroller interface | [`arduino_module`](https://github.com/AD-SDL/arduino_module) |
| Object detection | Vision based detection service | [`object_detection_module`](https://github.com/AD-SDL/object_detection_module) |
| AprilTag localization | Fiducial marker tracking | [`rpl_tag_engine_module`](https://github.com/AD-SDL/rpl_tag_engine_module) |
| FOM devices | Remote interfaces to facility owned instruments | [`fom_module`](https://github.com/AD-SDL/fom_module) |
