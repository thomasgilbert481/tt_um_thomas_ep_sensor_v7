drc euclidean on
cif istyle drc(full)
gds flatglob *
gds read /tmp/v7_baseline.gds
load tt_um_thomas_ep_sensor
select top cell
expand
drc check
drc catchup
set drc_err [drc count total]
puts "V7 BASELINE DRC: $drc_err"
quit -noprompt
