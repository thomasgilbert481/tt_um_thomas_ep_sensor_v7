# Netgen setup file for v9 LVS with parasitic capacitors ignored
# Source default setup, then add parasitic-C ignore directive

source /foss/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl

# Tell netgen to ignore parasitic capacitor classes named by Magic PEX
# Magic typically names parasitics as "c0", "c1", ... at the top level
ignore class -circuit1 capacitor

puts "netgen LVS: parasitic capacitor class ignored on circuit1"
