#!/bin/bash
set -e
KLAYOUT=/foss/tools/klayout/klayout
GDS=/foss/designs/tt_um_thomas_ep_sensor_v7/gds/tt_um_thomas_ep_sensor.gds
DRC=/foss/pdks/sky130A/libs.tech/klayout/drc/sky130A_mr.drc
REPORT=/tmp/v8_klayout_drc.lyrdb
echo "Running KLayout DRC on $GDS"
$KLAYOUT -b -r $DRC -rd "input=$GDS" -rd "report=$REPORT" -rd "thr=4" -rd "feol=true" -rd "beol=true" 2>&1 | tail -30
echo "--- Report summary ---"
python3 -c "
import re
with open('$REPORT') as f:
    content = f.read()
items = re.findall(r'<item[^>]*>', content)
print(f'Total DRC items: {len(items)}')
# Categorize by rule
cats = re.findall(r'<category>([^<]+)</category>', content)
from collections import Counter
counts = Counter(cats)
for k,v in counts.most_common(20):
    print(f'  {k}: {v}')
" 2>&1
