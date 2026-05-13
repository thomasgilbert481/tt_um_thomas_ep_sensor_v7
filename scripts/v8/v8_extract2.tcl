# Magic extraction script v2 - use proper ext2spice flow
gds flatglob *
gds read /foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds
load tt_um_thomas_ep_sensor
select top cell
expand
extract style ngspice(si)
extract no all
extract do all
extract unique
extract all
puts "Extract complete - writing ext files"
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice format ngspice
ext2spice -p . -o /tmp/v8_extracted.spice tt_um_thomas_ep_sensor
puts "Wrote /tmp/v8_extracted.spice"
quit -noprompt
