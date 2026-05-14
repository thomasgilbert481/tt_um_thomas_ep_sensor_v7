# v9 Task 2: hierarchical Magic PEX with port labels preserved
#
# Strategy:
# 1. Read GDS
# 2. Load top cell
# 3. Use 'port make default' to instantiate default ports from any port labels in the GDS
# 4. Hierarchical extract (no flatten)
# 5. Write top-level SPICE
#
# Output: /tmp/v9_pex_hier/

gds noduplicates true
gds rescale false
gds read /foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds
load tt_um_thomas_ep_sensor
select top cell

# Make default ports for labeled M4 pins (this picks up ua[0..7], ui_in[0..7], clk, etc.)
port make default

# Hierarchical extraction
extract path /tmp/v9_pex_hier
extract style ngspice(si)
extract no all
extract do resistance
extract do capacitance
extract do coupling
extract all

ext2spice lvs
ext2spice cthresh 0.001
ext2spice rthresh 1
ext2spice format ngspice
ext2spice hierarchy on
ext2spice subcircuits on
ext2spice -p /tmp/v9_pex_hier -o /tmp/v9_pex_hier/tt_pex_hier.spice tt_um_thomas_ep_sensor
puts "PEX done"
quit -noprompt
