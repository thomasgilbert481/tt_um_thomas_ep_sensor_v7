# Netgen LVS comparison: PEX'd v8 vs schematic v8
# Pass: 225 devices match, 0 net mismatches
readnet spice /tmp/v9_pex/tt_pex.spice
readnet spice /foss/designs/tt_um_thomas_ep_sensor_v7/src/ep_sensor_v8_schematic.spice

# Compare the top cells
lvs {"/tmp/v9_pex/tt_pex.spice" tt_um_thomas_ep_sensor} {"/foss/designs/tt_um_thomas_ep_sensor_v7/src/ep_sensor_v8_schematic.spice" tt_um_thomas_ep_sensor} /foss/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl /tmp/v9_lvs_out.txt -json -blackbox
