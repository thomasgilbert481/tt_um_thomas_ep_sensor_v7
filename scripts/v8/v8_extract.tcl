# Magic extraction script for v8 GDS
gds flatglob *
gds read /foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds
load tt_um_thomas_ep_sensor
select top cell
expand
cd /tmp/magic_extract
extract style ngspice(si)
extract path /tmp/magic_extract
extract no all
extract do all
extract unique
extract
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice format ngspice
ext2spice tt_um_thomas_ep_sensor /tmp/v8_extracted.spice
puts "Extraction done"
quit -noprompt
