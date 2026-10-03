import json
import sys

CONTRACT = "contracts/relay_receipt.py"
SENDER_URL = "https://sender.example.org/dispatch-7"
RECEIVER_URL = "https://receiver.example.net/intake-7"
SENDER_TEXT = "Dispatch receipt RR-7. Asset ID: rotor-77. Quantity received for transfer: 4 sealed units. Condition at departure: intact with security seal S-901."
RECEIVER_TEXT = "Intake receipt RR-7. Asset ID: rotor-77. Quantity counted at intake: 4 sealed units. Condition at arrival: intact with security seal S-901."


def addr(value):
    if hasattr(value, "as_hex"):
        return value.as_hex
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value)


def observation(condition="INTACT", quantity=4, identity="rotor-77", receiver=False):
    return json.dumps({
        "asset_id": identity,
        "quantity": quantity,
        "condition": condition,
        "identity_quote": "Asset ID: rotor-77",
        "quantity_quote": "Quantity counted at intake: 4 sealed units" if receiver else "Quantity received for transfer: 4 sealed units",
        "condition_quote": "Condition at arrival: intact with security seal S-901" if receiver else "Condition at departure: intact with security seal S-901",
    })


def enable_consensus(contract, monkeypatch, comparator=None):
    module = sys.modules[contract.__class__.__module__]
    monkeypatch.setattr(module.gl.eq_principle, "strict_eq", lambda fn: fn())
    monkeypatch.setattr(module.gl.eq_principle, "prompt_comparative", comparator or (lambda fn, *_args, **_kwargs: fn()))


def create_route(contract, vm, alice, bob, route_id="rotor-route"):
    vm.sender = alice
    return contract.create_route(route_id, "Rotor custody route", "rotor-77", 4, json.dumps([addr(alice), addr(bob)]), "0x" + "33" * 20)


def mock_sources(vm, receiver_text=RECEIVER_TEXT):
    vm.mock_web(SENDER_URL, {"method": "GET", "status": 200, "body": SENDER_TEXT})
    vm.mock_web(RECEIVER_URL, {"method": "GET", "status": 200, "body": receiver_text})


def test_contract_loads(direct_deploy):
    assert direct_deploy(CONTRACT) is not None


def test_route_identity_authority_and_duplicates(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("first custodian"):
        contract.create_route("wrong-owner", "Wrong owner", "rotor-77", 4, json.dumps([addr(direct_bob), addr(direct_alice)]), "0x" + "33" * 20)
    with direct_vm.expect_revert("independent"):
        contract.create_route("bad-inspector", "Bad inspector", "rotor-77", 4, json.dumps([addr(direct_alice), addr(direct_bob)]), direct_bob)
    create_route(contract, direct_vm, direct_alice, direct_bob)
    with direct_vm.expect_revert("already exists"):
        create_route(contract, direct_vm, direct_alice, direct_bob)


def test_matched_bilateral_handoff_moves_custody(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    contract = direct_deploy(CONTRACT); enable_consensus(contract, monkeypatch); create_route(contract, direct_vm, direct_alice, direct_bob)
    contract.propose_handoff("rotor-route", "dispatch-seven", direct_bob, SENDER_URL, observation())
    direct_vm.sender = direct_bob; mock_sources(direct_vm)
    result = contract.acknowledge_handoff("rotor-route", "dispatch-seven", RECEIVER_URL, observation(receiver=True))
    assert result["outcome"] == "MATCH" and result["route_status"] == "DELIVERED"
    route = contract.get_route("rotor-route")
    handoff = contract.get_handoff("rotor-route", "dispatch-seven")
    assert route["current_index"] == 1 and handoff["status"] == "ACCEPTED"
    assert len(handoff["result"]["source_receipts"]) == 2


def test_only_named_receiver_can_acknowledge(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    contract = direct_deploy(CONTRACT); enable_consensus(contract, monkeypatch); create_route(contract, direct_vm, direct_alice, direct_bob)
    contract.propose_handoff("rotor-route", "dispatch-seven", direct_bob, SENDER_URL, observation())
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("named receiver"):
        contract.acknowledge_handoff("rotor-route", "dispatch-seven", RECEIVER_URL, observation(receiver=True))


def test_forged_quote_fails_closed(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    contract = direct_deploy(CONTRACT); enable_consensus(contract, monkeypatch); create_route(contract, direct_vm, direct_alice, direct_bob)
    contract.propose_handoff("rotor-route", "dispatch-seven", direct_bob, SENDER_URL, observation())
    direct_vm.sender = direct_bob; mock_sources(direct_vm)
    forged = json.loads(observation(receiver=True)); forged["condition_quote"] = "Package was definitely intact"
    with direct_vm.expect_revert("quote is absent"):
        contract.acknowledge_handoff("rotor-route", "dispatch-seven", RECEIVER_URL, json.dumps(forged))


def test_condition_dispute_preserves_sender_custody_and_can_abort(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    contract = direct_deploy(CONTRACT); enable_consensus(contract, monkeypatch); create_route(contract, direct_vm, direct_alice, direct_bob)
    contract.propose_handoff("rotor-route", "dispatch-seven", direct_bob, SENDER_URL, observation())
    damaged_text = "Intake receipt RR-7. Asset ID: rotor-77. Quantity counted at intake: 4 sealed units. Condition at arrival: damaged housing and broken security seal S-901."
    damaged = json.loads(observation("DAMAGED", receiver=True)); damaged["condition_quote"] = "Condition at arrival: damaged housing and broken security seal S-901"
    direct_vm.sender = direct_bob; mock_sources(direct_vm, damaged_text)
    result = contract.acknowledge_handoff("rotor-route", "dispatch-seven", RECEIVER_URL, json.dumps(damaged))
    assert result["outcome"] == "CONDITION_CHANGED" and result["route_status"] == "DISPUTED"
    assert contract.get_route("rotor-route")["current_index"] == 0
    contract.abort_dispute("rotor-route", "dispatch-seven")
    assert contract.get_route("rotor-route")["status"] == "ABORTED"


def test_sender_can_cancel_unacknowledged_handoff(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT); create_route(contract, direct_vm, direct_alice, direct_bob)
    contract.propose_handoff("rotor-route", "dispatch-seven", direct_bob, SENDER_URL, observation())
    contract.cancel_proposed_handoff("rotor-route", "dispatch-seven")
    assert contract.get_route("rotor-route")["status"] == "ACTIVE"
    assert contract.get_handoff("rotor-route", "dispatch-seven")["status"] == "CANCELLED"


def test_comparator_cannot_change_bound_outcome(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    contract = direct_deploy(CONTRACT)
    def replace(fn, *_args, **_kwargs):
        row = json.loads(fn()); row["outcome"] = "QUANTITY_MISMATCH"; return json.dumps(row)
    enable_consensus(contract, monkeypatch, replace); create_route(contract, direct_vm, direct_alice, direct_bob)
    contract.propose_handoff("rotor-route", "dispatch-seven", direct_bob, SENDER_URL, observation())
    direct_vm.sender = direct_bob; mock_sources(direct_vm)
    with direct_vm.expect_revert("does not match"):
        contract.acknowledge_handoff("rotor-route", "dispatch-seven", RECEIVER_URL, observation(receiver=True))


def test_duplicate_evidence_identity_is_rejected(direct_vm, direct_deploy, direct_alice, direct_bob, monkeypatch):
    contract = direct_deploy(CONTRACT); enable_consensus(contract, monkeypatch); create_route(contract, direct_vm, direct_alice, direct_bob)
    contract.propose_handoff("rotor-route", "dispatch-seven", direct_bob, SENDER_URL, observation())
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("must be distinct"):
        contract.acknowledge_handoff("rotor-route", "dispatch-seven", SENDER_URL, observation(receiver=True))
