# Mechanism comparison

RelayReceipt is a bilateral custody transition, not a policy score, claim appeal, source succession, document merge, or multi-source chronology.

| Dimension | RelayReceipt |
| --- | --- |
| Parties | Ordered custodians plus an independent inspector slot |
| State-driving input | Two party-authored evidence records for one physical handoff |
| Consensus question | Do both condition labels faithfully represent their cited evidence? |
| Deterministic rule | Identity, quantity, then condition comparison in fixed priority |
| State transition | Custody moves only on a matched bilateral receipt |
| Failure behavior | Sender retains custody; route enters dispute or can be aborted |
| Reuse model | Any multi-hop custody chain can compose repeated handoffs |

The primitive introduced here is evidence-matched transfer of custody. Existing work in this account evaluates policies, verifies claims, tracks source evolution, or synthesizes narratives; none makes ownership of the next state conditional on a receiver-bound second receipt.
