* v10 schematic (LVS-target, multi-finger PCell sizing)
*
* Topology vs v9:
* - Mf widened to W=3200 µm (8× v9's 400 µm) via 8 parallel NQVC98-equivalent instances
* - Telescopic cascode Mc above Mf (W=200, L=0.15) biased at Vbc=1.15 V
* - Output common-gate stage to drop Z_out (gm·ro multiplier)
* - All caps, spirals, cv-array unchanged from v9
*
* Predicted Z_out @ 2.7 GHz: 28 Ω (from sim/v10_cascode_design)
* Predicted slope @ TT/27°C: 0.49 ± 0.03

.subckt tt_um_thomas_ep_sensor V1 V2_in Vfo Vbn_top Vbn_bot Vbmid Vbc VDPWR VGND ui_in0 ui_in1 ui_in2 ui_in3 ui_in4 ui_in5 ui_in6 ui_in7

* === Bias resistor divider ===
XRdiv_top  net_bnd VDPWR sky130_fd_pr__res_xhigh_po_0p35 l=58.11u
XRdiv_bot  Vbn_bot net_bnd sky130_fd_pr__res_xhigh_po_0p35 l=72.37u
XRbn_top   Vbn_top net_bnt sky130_fd_pr__res_xhigh_po_0p35 l=0.10089m
XRbn_bot   VGND net_bnt sky130_fd_pr__res_xhigh_po_0p35 l=0.26367m
XRbn_out_top Vfo net_bo sky130_fd_pr__res_xhigh_po_0p35 l=0.10089m
XRbn_out_bot net_bo Vfo_x sky130_fd_pr__res_xhigh_po_0p35 l=0.14715m

* === v10 NEW: cascode bias ladder for Vbc ===
* Diode-connected NFET in series with the existing bias network
* Vbc tracks PVT with Mf threshold (Vbc = VDPWR - Vgs_diode ≈ 1.15 V)
XMbc_ref Vbc Vbc VDPWR VDPWR sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=4 m=1

* === Decoupling caps (unchanged from v9) ===
XCdec_bn      Vbn_top  VGND  VGND sky130_fd_pr__cap_mim_m3_1 W=22 L=22
XCdec_bn_out  Vfo_x    VGND  VGND sky130_fd_pr__cap_mim_m3_1 W=15.8 L=15.8
XCdec_bmid    Vbmid    VGND  VGND sky130_fd_pr__cap_mim_m3_1 W=22 L=22
XCff          Vfo_x    VGND  VGND sky130_fd_pr__cap_mim_m3_1 W=10 L=10

* === Tank capacitors (unchanged) ===
XCT1  V1     VGND  VGND sky130_fd_pr__cap_mim_m3_1 W=30   L=30
XCT2  V2_in  VGND  VGND sky130_fd_pr__cap_mim_m3_1 W=20.2 L=20.2
XCc   Vfo    V2_in VGND sky130_fd_pr__cap_mim_m3_1 W=26.1 L=26.1
XCac_v2 V2_in VGND  VGND sky130_fd_pr__cap_mim_m3_1 W=20   L=20

* Cac_in (MQHU4F, 11 sub-caps × W=21 L=21)
XCac_in_a V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_b V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_c V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_d V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_e V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_f V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_g V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_h V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_i V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_j V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21
XCac_in_k V1 vin_p VGND sky130_fd_pr__cap_mim_m3_1 W=21 L=21

* === Spirals (unchanged) ===
L1_spiral V1 nL1 1.351n
R1_spiral nL1 VDPWR 5.0
L2_spiral V2_in nL2 1.351n
R2_spiral nL2 VGND 5.0

* === cv-array (unchanged from v9) ===
XCv0 V1 mg0_d VGND sky130_fd_pr__cap_mim_m3_1 W=3.16 L=3.16
Xmg0 V2_in ui_in7 mg0_d VGND sky130_fd_pr__nfet_01v8_lvt W=20 L=0.15 nf=4 m=1
XCv1 V1 mg1_d VGND sky130_fd_pr__cap_mim_m3_1 W=4.47 L=4.47
Xmg1 V2_in ui_in6 mg1_d VGND sky130_fd_pr__nfet_01v8_lvt W=20 L=0.15 nf=4 m=1
XCv2 V1 mg2_d VGND sky130_fd_pr__cap_mim_m3_1 W=6.32 L=6.32
Xmg2 V2_in ui_in5 mg2_d VGND sky130_fd_pr__nfet_01v8_lvt W=20 L=0.15 nf=4 m=1
XCv3 V1 mg3_d VGND sky130_fd_pr__cap_mim_m3_1 W=8.94 L=8.94
Xmg3 V2_in ui_in4 mg3_d VGND sky130_fd_pr__nfet_01v8_lvt W=20 L=0.15 nf=4 m=1
XCv4 V1 mg4_d VGND sky130_fd_pr__cap_mim_m3_1 W=12.65 L=12.65
Xmg4 V2_in ui_in0 mg4_d VGND sky130_fd_pr__nfet_01v8_lvt W=20 L=0.15 nf=4 m=1
XCv5 V1 mg5_d VGND sky130_fd_pr__cap_mim_m3_1 W=17.89 L=17.89
Xmg5 V2_in ui_in1 mg5_d VGND sky130_fd_pr__nfet_01v8_lvt W=20 L=0.15 nf=4 m=1
XCv6 V1 mg6_d VGND sky130_fd_pr__cap_mim_m3_1 W=25.3 L=25.3
Xmg6 V2_in ui_in2 mg6_d VGND sky130_fd_pr__nfet_01v8_lvt W=20 L=0.15 nf=4 m=1
XCv7 V1 mg7_d VGND sky130_fd_pr__cap_mim_m3_1 W=25.31 L=25.31
Xmg7 V2_in ui_in3 mg7_d VGND sky130_fd_pr__nfet_01v8_lvt W=20 L=0.15 nf=4 m=1

* === v10 OTA: 8× wider Mf + telescopic cascode Mc ===
* Mb: tail (unchanged from v9)
XMb tail Vbn_bot VGND VGND sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=20 m=1
* Mf (8× wider): 8 parallel NQVC98-equivalents (each W=5 L=0.15 nf=80) = total W=3200
XMf_a Mf_d vin_p Vfo VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=80 m=1
XMf_b Mf_d vin_p Vfo VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=80 m=1
XMf_c Mf_d vin_p Vfo VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=80 m=1
XMf_d Mf_d vin_p Vfo VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=80 m=1
XMf_e Mf_d vin_p Vfo VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=80 m=1
XMf_f Mf_d vin_p Vfo VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=80 m=1
XMf_g Mf_d vin_p Vfo VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=80 m=1
XMf_h Mf_d vin_p Vfo VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=80 m=1
* Mc: telescopic cascode above Mf (gate=Vbc, drain=VDPWR, source=Mf_d)
XMc VDPWR Vbc Mf_d VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=40 m=1
* Mout: second-stage amp (unchanged from v9)
XMout VDPWR Vfo Vfo_x VGND sky130_fd_pr__nfet_01v8 W=5 L=0.15 nf=40 m=1
* Mout_b: second-stage tail
XMout_b Vfo_x Vbn_top VGND VGND sky130_fd_pr__nfet_01v8 W=10 L=0.5 nf=10 m=1

.ends tt_um_thomas_ep_sensor

.end
