"""Adversarial Attack Scenario Injector simulating realistic financial fraud syndicates across time."""

from __future__ import annotations

import random
from typing import List, Tuple
from simulation.generator import MultiEntitySimulator
from simulation.models import AttackType, Transaction


class AdversarialAttackInjector:
    """Injects 6 distinct real-world financial fraud patterns distributed across the entire transaction timeline."""

    def __init__(self, simulator: MultiEntitySimulator, seed: int = 42):
        self.sim = simulator
        random.seed(seed)

    def inject_all_attacks(
        self,
        base_transactions: List[Transaction],
        fraud_ratio: float = 0.05,
    ) -> List[Transaction]:
        """Injects a calibrated mix of adversarial attacks into the transaction stream across all time horizons."""
        augmented_txs = list(base_transactions)
        target_fraud_count = int(len(base_transactions) * fraud_ratio)
        per_attack = max(6, target_fraud_count // 6)

        t_min = min(t.timestamp for t in base_transactions) if base_transactions else 1714521600.0
        t_max = max(t.timestamp for t in base_transactions) if base_transactions else 1714521600.0 + 86400 * 3
        t_span = max(3600.0, t_max - t_min)

        tx_counter = len(base_transactions) + 1000

        # Anchor times spanning train (20%), val (75%), and test (90%)
        # 1. VELOCITY_BURST
        tx_counter, v_txs = self._inject_velocity_burst(tx_counter, count=per_attack, t_min=t_min, t_span=t_span)
        augmented_txs.extend(v_txs)

        # 2. DEVICE_SHARING_RING
        tx_counter, d_txs = self._inject_device_sharing_ring(tx_counter, count=per_attack, t_min=t_min, t_span=t_span)
        augmented_txs.extend(d_txs)

        # 3. IMPOSSIBLE_TRAVEL
        tx_counter, t_txs = self._inject_impossible_travel(tx_counter, count=per_attack, t_min=t_min, t_span=t_span)
        augmented_txs.extend(t_txs)

        # 4. IP_PROXY_CLUSTER
        tx_counter, ip_txs = self._inject_ip_proxy_cluster(tx_counter, count=per_attack, t_min=t_min, t_span=t_span)
        augmented_txs.extend(ip_txs)

        # 5. MERCHANT_COLLUSION
        tx_counter, m_txs = self._inject_merchant_collusion(tx_counter, count=per_attack, t_min=t_min, t_span=t_span)
        augmented_txs.extend(m_txs)

        # 6. ACCOUNT_TAKEOVER
        tx_counter, ato_txs = self._inject_account_takeover(tx_counter, count=per_attack, t_min=t_min, t_span=t_span)
        augmented_txs.extend(ato_txs)

        # Re-sort by timestamp to preserve streaming chronological sequence
        augmented_txs.sort(key=lambda x: x.timestamp)
        return augmented_txs

    def _inject_velocity_burst(self, counter: int, count: int, t_min: float, t_span: float) -> Tuple[int, List[Transaction]]:
        txs = []
        attacker_device = random.choice(self.sim.devices)
        attacker_ip = random.choice(self.sim.ips)
        target_merchant = random.choice([m for m in self.sim.merchants if m.risk_tier == "HIGH_RISK"] or self.sim.merchants)

        # Distribute into multiple bursts across early, mid, and late stream
        burst_anchors = [t_min + t_span * frac for frac in [0.25, 0.72, 0.90]]

        for i in range(count):
            counter += 1
            user = random.choice(self.sim.users)
            card = random.choice(self.sim.cards)
            base_t = burst_anchors[i % len(burst_anchors)]
            txs.append(
                Transaction(
                    tx_id=f"TXN_FRD_VEL_{counter:06d}",
                    user_id=user.user_id,
                    card_id=card.card_id,
                    device_id=attacker_device.device_id,
                    ip_address=attacker_ip.ip_address,
                    merchant_id=target_merchant.merchant_id,
                    address_id=random.choice(self.sim.addresses).address_id,
                    amount=round(random.uniform(15.0, 45.0), 2),
                    timestamp=base_t + ((i // len(burst_anchors)) * 12.0),
                    channel="ONLINE",
                    is_fraud=1,
                    attack_type=AttackType.VELOCITY_BURST,
                    fraud_label_delay_days=random.randint(14, 45),
                    ground_truth_reasons=[
                        "Carding bot burst: >10 transactions within 3 minutes from single device",
                        "High card rotation across distinct cardholder identities",
                    ],
                )
            )
        return counter, txs

    def _inject_device_sharing_ring(self, counter: int, count: int, t_min: float, t_span: float) -> Tuple[int, List[Transaction]]:
        txs = []
        syndicate_device = random.choice(self.sim.devices)
        syndicate_users = random.sample(self.sim.users, min(15, len(self.sim.users)))
        anchors = [t_min + t_span * frac for frac in [0.30, 0.75, 0.92]]

        for i in range(count):
            counter += 1
            user = syndicate_users[i % len(syndicate_users)]
            card = random.choice(self.sim.cards)
            base_t = anchors[i % len(anchors)]
            txs.append(
                Transaction(
                    tx_id=f"TXN_FRD_RING_{counter:06d}",
                    user_id=user.user_id,
                    card_id=card.card_id,
                    device_id=syndicate_device.device_id,
                    ip_address=random.choice(self.sim.ips).ip_address,
                    merchant_id=random.choice(self.sim.merchants).merchant_id,
                    address_id=random.choice(self.sim.addresses).address_id,
                    amount=round(random.uniform(120.0, 480.0), 2),
                    timestamp=base_t + ((i // len(anchors)) * 300.0),
                    channel="ONLINE",
                    is_fraud=1,
                    attack_type=AttackType.DEVICE_SHARING_RING,
                    fraud_label_delay_days=random.randint(21, 60),
                    ground_truth_reasons=[
                        "Device-sharing fraud ring: 1 device shared by >10 distinct user accounts",
                        "High-degree hardware graph hub indicating syndicate mule operation",
                    ],
                )
            )
        return counter, txs

    def _inject_impossible_travel(self, counter: int, count: int, t_min: float, t_span: float) -> Tuple[int, List[Transaction]]:
        txs = []
        user = random.choice(self.sim.users)
        card = random.choice([c for c in self.sim.cards if c.user_id == user.user_id] or self.sim.cards)
        anchors = [t_min + t_span * frac for frac in [0.20, 0.78, 0.88]]

        ny_ip = next((ip for ip in self.sim.ips if ip.country == "US"), self.sim.ips[0])
        london_ip = next((ip for ip in self.sim.ips if ip.country == "GB"), self.sim.ips[-1])

        for i in range(count):
            counter += 1
            is_uk = (i % 2 == 1)
            base_t = anchors[i % len(anchors)]
            txs.append(
                Transaction(
                    tx_id=f"TXN_FRD_GEO_{counter:06d}",
                    user_id=user.user_id,
                    card_id=card.card_id,
                    device_id=random.choice(self.sim.devices).device_id,
                    ip_address=london_ip.ip_address if is_uk else ny_ip.ip_address,
                    merchant_id=random.choice(self.sim.merchants).merchant_id,
                    address_id=random.choice(self.sim.addresses).address_id,
                    amount=round(random.uniform(200.0, 850.0), 2),
                    timestamp=base_t + ((i // len(anchors)) * 900.0),
                    channel="ONLINE",
                    is_fraud=1,
                    attack_type=AttackType.IMPOSSIBLE_TRAVEL,
                    fraud_label_delay_days=random.randint(14, 30),
                    ground_truth_reasons=[
                        "Impossible travel speed: Transacted in New York and London within 15 minutes",
                        "Calculated velocity exceeds 2,500 km/h (physical travel threshold)",
                    ],
                )
            )
        return counter, txs

    def _inject_ip_proxy_cluster(self, counter: int, count: int, t_min: float, t_span: float) -> Tuple[int, List[Transaction]]:
        txs = []
        proxy_ip = random.choice([ip for ip in self.sim.ips if ip.is_vpn or ip.is_datacenter] or self.sim.ips)
        anchors = [t_min + t_span * frac for frac in [0.35, 0.70, 0.95]]

        for i in range(count):
            counter += 1
            user = random.choice(self.sim.users)
            card = random.choice(self.sim.cards)
            base_t = anchors[i % len(anchors)]
            txs.append(
                Transaction(
                    tx_id=f"TXN_FRD_PRX_{counter:06d}",
                    user_id=user.user_id,
                    card_id=card.card_id,
                    device_id=random.choice(self.sim.devices).device_id,
                    ip_address=proxy_ip.ip_address,
                    merchant_id=random.choice(self.sim.merchants).merchant_id,
                    address_id=random.choice(self.sim.addresses).address_id,
                    amount=round(random.uniform(80.0, 350.0), 2),
                    timestamp=base_t + ((i // len(anchors)) * 200.0),
                    channel="ONLINE",
                    is_fraud=1,
                    attack_type=AttackType.IP_PROXY_CLUSTER,
                    fraud_label_delay_days=random.randint(20, 50),
                    ground_truth_reasons=[
                        "Anonymizing proxy / bulletproof VPN IP cluster detected",
                        "Multiple disparate cardholders originating from single datacenter IP",
                    ],
                )
            )
        return counter, txs

    def _inject_merchant_collusion(self, counter: int, count: int, t_min: float, t_span: float) -> Tuple[int, List[Transaction]]:
        txs = []
        collusive_merchant = random.choice([m for m in self.sim.merchants if m.risk_tier == "HIGH_RISK"] or self.sim.merchants)
        anchors = [t_min + t_span * frac for frac in [0.15, 0.65, 0.85]]

        for i in range(count):
            counter += 1
            user = random.choice(self.sim.users)
            card = random.choice(self.sim.cards)
            base_t = anchors[i % len(anchors)]
            txs.append(
                Transaction(
                    tx_id=f"TXN_FRD_MKT_{counter:06d}",
                    user_id=user.user_id,
                    card_id=card.card_id,
                    device_id=random.choice(self.sim.devices).device_id,
                    ip_address=random.choice(self.sim.ips).ip_address,
                    merchant_id=collusive_merchant.merchant_id,
                    address_id=random.choice(self.sim.addresses).address_id,
                    amount=round(random.choice([950.0, 980.0, 990.0, 1000.0]), 2),
                    timestamp=base_t + ((i // len(anchors)) * 600.0),
                    channel="ONLINE",
                    is_fraud=1,
                    attack_type=AttackType.MERCHANT_COLLUSION,
                    fraud_label_delay_days=random.randint(30, 90),
                    ground_truth_reasons=[
                        "Merchant collusion / bust-out pattern: Round high-value transaction clustering",
                        "High chargeback merchant volume surge without physical storefront verification",
                    ],
                )
            )
        return counter, txs

    def _inject_account_takeover(self, counter: int, count: int, t_min: float, t_span: float) -> Tuple[int, List[Transaction]]:
        txs = []
        victim_user = random.choice([u for u in self.sim.users if u.account_age_days > 180] or self.sim.users)
        victim_card = random.choice([c for c in self.sim.cards if c.user_id == victim_user.user_id] or self.sim.cards)
        attacker_device = random.choice([d for d in self.sim.devices if d.is_emulator] or self.sim.devices)
        attacker_ip = random.choice([ip for ip in self.sim.ips if ip.country != "US"] or self.sim.ips)
        anchors = [t_min + t_span * frac for frac in [0.40, 0.80, 0.96]]

        for i in range(count):
            counter += 1
            base_t = anchors[i % len(anchors)]
            txs.append(
                Transaction(
                    tx_id=f"TXN_FRD_ATO_{counter:06d}",
                    user_id=victim_user.user_id,
                    card_id=victim_card.card_id,
                    device_id=attacker_device.device_id,
                    ip_address=attacker_ip.ip_address,
                    merchant_id=random.choice(self.sim.merchants).merchant_id,
                    address_id=random.choice(self.sim.addresses).address_id,
                    amount=round(random.uniform(450.0, 1200.0), 2),
                    timestamp=base_t + ((i // len(anchors)) * 180.0),
                    channel="ONLINE",
                    is_fraud=1,
                    attack_type=AttackType.ACCOUNT_TAKEOVER,
                    fraud_label_delay_days=random.randint(14, 30),
                    ground_truth_reasons=[
                        "Account Takeover (ATO): Established account suddenly active on emulator device",
                        "Unprecedented foreign IP address combined with 6x historical spend spike",
                    ],
                )
            )
        return counter, txs
