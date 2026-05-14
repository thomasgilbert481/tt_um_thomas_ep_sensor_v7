"""Strip parasitic capacitor + Magic $ devices from PEX'd SPICE netlist
to enable netgen LVS device-count match.
"""
import re, sys

IN = "/tmp/v9_pex_hier/tt_pex_hier.spice"
OUT = "/tmp/v9_pex_hier/tt_pex_active.spice"

n_skip_cap = 0
n_skip_well = 0
n_keep = 0
with open(IN) as f_in, open(OUT, 'w') as f_out:
    skip = False
    for line in f_in:
        # Magic "$" device: starts with "$"
        if re.match(r"^\$\s+", line):
            n_skip_well += 1
            continue
        # Parasitic cap: line starts with C<digits> <node1> <node2> <value>
        if re.match(r"^C[0-9]+\s+", line):
            n_skip_cap += 1
            continue
        f_out.write(line)
        n_keep += 1

print(f"Stripped {n_skip_cap} parasitic capacitors")
print(f"Stripped {n_skip_well} Magic $ devices")
print(f"Kept {n_keep} lines, wrote {OUT}")
