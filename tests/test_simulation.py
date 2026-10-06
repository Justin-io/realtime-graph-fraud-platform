"""Unit tests for multi-entity simulator and adversarial attack generator."""

import pytest
from simulation.generator import MultiEntitySimulator
from simulation.attacks import AdversarialAttackInjector
from simulation.models import AttackType


def test_entity_generation():
    sim = MultiEntitySimulator(seed=42)
    entities = sim.generate_entities(
        n_users=100,
        n_cards=150,
        n_devices=120,
        n_ips=80,
        n_merchants=20,
        n_addresses=100,
    )

    assert len(entities["users"]) == 100
    assert len(entities["cards"]) == 150
    assert len(entities["devices"]) == 120
    assert len(entities["ips"]) == 80
    assert len(entities["merchants"]) == 20
    assert len(entities["addresses"]) == 100

    # Ensure foreign keys connect
    card_user_ids = {c.user_id for c in entities["cards"]}
    all_user_ids = {u.user_id for u in entities["users"]}
    assert card_user_ids.issubset(all_user_ids)


def test_benign_transaction_generation():
    sim = MultiEntitySimulator(seed=42)
    sim.generate_entities(n_users=50, n_cards=80, n_devices=60, n_ips=40, n_merchants=10, n_addresses=50)
    txs = sim.generate_benign_transactions(n_transactions=500)

    assert len(txs) == 500
    assert all(tx.is_fraud == 0 for tx in txs)
    assert all(tx.attack_type == AttackType.NONE for tx in txs)
    assert all(tx.amount > 0 for tx in txs)
    # Check chronological ordering
    timestamps = [t.timestamp for t in txs]
    assert timestamps == sorted(timestamps)


def test_adversarial_attack_injection():
    sim = MultiEntitySimulator(seed=42)
    sim.generate_entities(n_users=100, n_cards=150, n_devices=100, n_ips=80, n_merchants=20, n_addresses=100)
    benign_txs = sim.generate_benign_transactions(n_transactions=1000)

    injector = AdversarialAttackInjector(sim, seed=42)
    augmented_txs = injector.inject_all_attacks(benign_txs, fraud_ratio=0.08)

    assert len(augmented_txs) > len(benign_txs)
    fraud_txs = [tx for tx in augmented_txs if tx.is_fraud == 1]
    assert len(fraud_txs) > 0

    attack_types_present = {tx.attack_type for tx in fraud_txs}
    assert AttackType.VELOCITY_BURST in attack_types_present
    assert AttackType.DEVICE_SHARING_RING in attack_types_present
    assert AttackType.IMPOSSIBLE_TRAVEL in attack_types_present
    assert AttackType.IP_PROXY_CLUSTER in attack_types_present
    assert AttackType.MERCHANT_COLLUSION in attack_types_present
    assert AttackType.ACCOUNT_TAKEOVER in attack_types_present

    # Verify delayed chargeback labels are simulated (14-90 days)
    assert all(tx.fraud_label_delay_days >= 14 for tx in fraud_txs)
    # Verify ground truth reasons exist
    assert all(len(tx.ground_truth_reasons) > 0 for tx in fraud_txs)
