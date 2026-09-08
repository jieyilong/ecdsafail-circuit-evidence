# Coordinate-Phase Diagnosis

The original four profiles share a phase-only failure at development case **6828**, batch 106, lane 44. The trace first records its phase increment in the initial x subtraction. Subsequent stages have zero net phase delta on that lane, not a proof that every internal phase operation was correct.

| Stage | Start op | End op | Phase delta | Cumulative phase |
|---|---|---|---|---|
| start | 0 | 0 | 0x0000000000000000 | 0x0000000000000000 |
| tlm_coord_x_sub | 0 | 6608 | 0x0000100000000000 | 0x0000100000000000 |
| tlm_coord_y_sub | 6608 | 13216 | 0x0000000000000000 | 0x0000100000000000 |
| tlm_inverse | 13216 | 7360927 | 0x0000000000000000 | 0x0000100000000000 |
| tlm_coord_add3x | 7360927 | 7402394 | 0x0000000000000000 | 0x0000100000000000 |
| tlm_square | 7402394 | 7402394 | 0x0000000000000000 | 0x0000100000000000 |
| square_product_register | 7402394 | 8345745 | 0x0000000000000000 | 0x0000100000000000 |
| tlm_forward_multiply | 8345745 | 15697858 | 0x0000000000000000 | 0x0000100000000000 |
| tlm_coord_y_sub_final | 15697858 | 15704466 | 0x0000000000000000 | 0x0000100000000000 |
| tlm_coord_rsub_final | 15704466 | 15716533 | 0x0000000000000000 | 0x0000100000000000 |

The 19-bit coordinate-prefix check misses a lower-bit carry. Widening that check to 40 removes this development failure at about 72 extra mean Toffolis and unchanged Q. [All profile outcomes for this case](case-6828.json) are retained. The diagnostic log's inherited overall-shot denominator is not a sample-size claim for the selected-batch trace.
