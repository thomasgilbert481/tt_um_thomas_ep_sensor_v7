# Magic PEX v3 - don't flatten, preserve cell hierarchy
gds read /foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds
load tt_um_thomas_ep_sensor
select top cell
expand

# Extraction setup
extract path /tmp/v9_pex
extract style ngspice(si)
extract no all
extract do resistance
extract do capacitance
extract do coupling
extract all

puts "step1 done; check .ext files"

# ext2spice with parasitics
ext2spice lvs
ext2spice cthresh 0.001
ext2spice rthresh 1
ext2spice format ngspice
ext2spice -p /tmp/v9_pex -o /tmp/v9_pex/tt_pex.spice tt_um_thomas_ep_sensor
puts "step2 done"
quit -noprompt
