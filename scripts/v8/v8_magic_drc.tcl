drc euclidean on
cif istyle drc(full)
gds flatglob *
gds read /foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds
load tt_um_thomas_ep_sensor
select top cell
expand
drc check
drc catchup
set drc_err [drc count total]
puts "TOTAL DRC ERRORS: $drc_err"
quit -noprompt
