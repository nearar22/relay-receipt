# RelayReceipt

A custody transfer should not become true because one party clicked "received." RelayReceipt advances custody only after the named receiver submits a second evidence record and GenLayer validators verify both sides against the pages they cite.

## The manifest

A route fixes four things before movement begins: the asset identifier, exact quantity, ordered custodians, and an inspector who is not one of those custodians. The current custodian can offer the asset only to the next named address. The receiver must answer with a different evidence document.

Each document carries exact quotes for identity, quantity, and condition. Validators fetch both public HTTPS pages, bind their contents to SHA-256 receipts, and check that the structured observations faithfully describe the cited text. Contract code derives one of four outcomes:

- `MATCH`: identity, quantity, and condition agree; custody advances.
- `IDENTITY_MISMATCH`: either record names a different asset.
- `QUANTITY_MISMATCH`: either record changes the fixed count.
- `CONDITION_CHANGED`: the receiver reports a different condition.

A discrepancy leaves custody with the sender and places the route in `DISPUTED`. Either handoff party can abort safely, so an unavailable inspector cannot trap the record. An unacknowledged sender can also cancel and retry.

## Why this is an Intelligent Contract

Plain code can compare numbers and identifiers, but evidence documents describe condition in natural language. RelayReceipt uses comparative validator consensus to decide whether `INTACT`, `DAMAGED`, `OPENED`, or `UNKNOWN` faithfully represents each exact quote. The validator boundary covers every stored observation field and the derived outcome. A matching label with different quotes or quantities is rejected.

## Trust boundary

RelayReceipt records evidence-backed custody statements. It does not authenticate the organizations behind submitted URLs, inspect a physical object, or prove that a demo document came from an independent company. The included sender and receiver pages are operator-created fixtures used only to reproduce the contract flow.

## Lifecycle

```text
ACTIVE -> PENDING -> ACCEPTED -> ACTIVE or DELIVERED
                 -> DISPUTED -> ABORTED
ACTIVE -> PENDING -> CANCELLED -> ACTIVE
```

## Verify

```bash
python -m pytest tests -q -p no:cacheprovider
genvm-lint lint contracts/relay_receipt.py --json
npm run deploy
npm run smoke
npm run verify
```

The deployment scripts target GenLayer Studio Next, chain `61997`. Live addresses and transaction evidence are recorded in `deployment.json` after deployment.

## Live deployment

- Network: GenLayer Studio Next, chain `61997`
- Contract: [`0xa9fCc0Fd92Cf74f675bCAc10539Bd65C8CaC3C02`](https://explorer-studio-dev.genlayer.com/address/0xa9fCc0Fd92Cf74f675bCAc10539Bd65C8CaC3C02)
- Deployment transaction: [`0x9435fca6...8b6694bf`](https://explorer-studio-dev.genlayer.com/tx/0x9435fca62dffd2d2f3f6a0fc854255b0f5222eece2ea1ef8f495632f8b6694bf)
- Public demo route: `relay-demo-musmsxw2`
- Exact deployed source SHA-256: `d68c05a41455332607feed8ce8a228445296823310d72393b2a6b65a6f344593`

The live demonstration uses two separate wallet addresses. The sender creates the route and proposes a handoff; the named receiver submits the second receipt. Validator consensus returns `MATCH`, the handoff becomes `ACCEPTED`, and the route advances to `DELIVERED`. Both source pages remain explicitly labeled operator-created fixtures.

## Repository map

- `contracts/relay_receipt.py`: contract, evidence binding, consensus, and custody state machine
- `tests/`: authorization, lifecycle, recovery, forged quote, and adversarial consensus tests
- `docs/`: clearly labeled evidence fixtures and design comparison
- `scripts/`: deployment, two-wallet live lifecycle, and deployed-source verification
