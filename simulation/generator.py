"""Multi-Entity Simulator generating high-throughput realistic financial entities and baseline transactions."""

from __future__ import annotations

import hashlib
import math
import random
import time
from typing import Dict, List, Tuple
from simulation.models import (
    Address,
    AttackType,
    Card,
    Device,
    IPAddress,
    Merchant,
    Transaction,
    User,
)


class MultiEntitySimulator:
    """Generates synthetic multi-entity ecosystems and benign financial transactions."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.users: List[User] = []
        self.cards: List[Card] = []
        self.devices: List[Device] = []
        self.ips: List[IPAddress] = []
        self.merchants: List[Merchant] = []
        self.addresses: List[Address] = []

    def generate_entities(
        self,
        n_users: int = 500,
        n_cards: int = 700,
        n_devices: int = 600,
        n_ips: int = 400,
        n_merchants: int = 50,
        n_addresses: int = 500,
        base_timestamp: float = 1714521600.0,  # 2024-05-01 00:00:00 UTC
    ) -> Dict[str, List[Any]]:
        # 1. Users
        self.users = []
        for i in range(1, n_users + 1):
            uid = f"USR_{i:06d}"
            signup_offset = random.uniform(10 * 86400, 365 * 86400)
            self.users.append(
                User(
                    user_id=uid,
                    name=f"Customer {i}",
                    signup_timestamp=base_timestamp - signup_offset,
                    kyc_level=random.choices([1, 2, 3], weights=[0.2, 0.6, 0.2])[0],
                    account_age_days=round(signup_offset / 86400.0, 1),
                    base_risk=round(random.betavariate(1.5, 20.0), 4),
                )
            )

        # 2. Devices
        self.devices = []
        os_list = ["iOS", "Android", "macOS", "Windows", "Linux"]
        browsers = ["Safari", "Chrome", "Firefox", "Edge"]
        for i in range(1, n_devices + 1):
            did = f"DEV_{i:06d}"
            os_name = random.choice(os_list)
            browser = random.choice(browsers)
            fingerprint = hashlib.sha256(f"{did}_{os_name}_{browser}_{i}".encode()).hexdigest()[:16]
            self.devices.append(
                Device(
                    device_id=did,
                    os_name=os_name,
                    browser_name=browser,
                    is_emulator=random.random() < 0.02,
                    is_rooted=random.random() < 0.03,
                    fingerprint_hash=fingerprint,
                )
            )

        # 3. IPs
        self.ips = []
        cities = [
            ("New York", "US", 40.7128, -74.0060),
            ("San Francisco", "US", 37.7749, -122.4194),
            ("Chicago", "US", 41.8781, -87.6298),
            ("London", "GB", 51.5074, -0.1278),
            ("Toronto", "CA", 43.6532, -79.3832),
            ("Singapore", "SG", 1.3521, 103.8198),
        ]
        for i in range(1, n_ips + 1):
            ip_str = f"198.51.100.{i % 250 + 1}" if i <= 250 else f"203.0.113.{i % 250 + 1}"
            city, country, lat, lon = random.choice(cities)
            self.ips.append(
                IPAddress(
                    ip_address=ip_str,
                    asn=random.choice([15169, 16509, 13335, 7922, 32934]),
                    country=country,
                    is_vpn=random.random() < 0.05,
                    is_tor=random.random() < 0.01,
                    is_datacenter=random.random() < 0.04,
                    latitude=lat + random.uniform(-0.05, 0.05),
                    longitude=lon + random.uniform(-0.05, 0.05),
                )
            )

        # 4. Addresses
        self.addresses = []
        for i in range(1, n_addresses + 1):
            aid = f"ADDR_{i:06d}"
            city, country, lat, lon = random.choice(cities)
            self.addresses.append(
                Address(
                    address_id=aid,
                    street=f"{random.randint(10, 999)} Financial Way",
                    city=city,
                    country=country,
                    postal_code=f"{random.randint(10000, 99999)}",
                    is_po_box=random.random() < 0.04,
                    latitude=lat + random.uniform(-0.02, 0.02),
                    longitude=lon + random.uniform(-0.02, 0.02),
                )
            )

        # 5. Cards (bound to users)
        self.cards = []
        for i in range(1, n_cards + 1):
            cid = f"CRD_{i:06d}"
            user = random.choice(self.users)
            self.cards.append(
                Card(
                    card_id=cid,
                    user_id=user.user_id,
                    card_brand=random.choices(["Visa", "Mastercard", "Amex"], weights=[0.5, 0.35, 0.15])[0],
                    card_type=random.choices(["Debit", "Credit", "Prepaid"], weights=[0.55, 0.40, 0.05])[0],
                    issuer_country="US",
                    created_timestamp=user.signup_timestamp + random.uniform(60, 86400 * 5),
                )
            )

        # 6. Merchants
        self.merchants = []
        mcc_categories = [
            ("MERC_GROCERY", "Supermarket Express", "5411", "LOW", 45.0),
            ("MERC_ELEC", "NextGen Electronics", "5732", "STANDARD", 250.0),
            ("MERC_STREAM", "Cloudstream Entertainment", "4899", "LOW", 14.99),
            ("MERC_JEWEL", "Luxe Diamond Exchange", "5944", "HIGH_RISK", 850.0),
            ("MERC_TRAVEL", "Global Air & Travel", "4511", "STANDARD", 420.0),
            ("MERC_GAMING", "Fortune Digital Casino", "7995", "HIGH_RISK", 120.0),
            ("MERC_CAFE", "Daily Roast Cafe", "5812", "LOW", 8.50),
        ]
        for i in range(1, n_merchants + 1):
            mid = f"MKT_{i:04d}"
            preset = random.choice(mcc_categories)
            self.merchants.append(
                Merchant(
                    merchant_id=mid,
                    merchant_name=f"{preset[1]} #{i}",
                    mcc_code=preset[2],
                    risk_tier=preset[3],
                    avg_amount=preset[4],
                )
            )

        return {
            "users": self.users,
            "cards": self.cards,
            "devices": self.devices,
            "ips": self.ips,
            "merchants": self.merchants,
            "addresses": self.addresses,
        }

    def generate_benign_transactions(
        self,
        n_transactions: int = 5000,
        start_timestamp: float = 1714521600.0,
        duration_hours: float = 72.0,
    ) -> List[Transaction]:
        """Generates realistic benign transactional activity with diurnal curves and log-normal amounts."""
        transactions: List[Transaction] = []
        end_timestamp = start_timestamp + duration_hours * 3600.0

        for i in range(1, n_transactions + 1):
            tx_id = f"TXN_{i:08d}"
            # Random time distributed over duration
            t = random.uniform(start_timestamp, end_timestamp)
            
            # Select user and their card
            user = random.choice(self.users)
            user_cards = [c for c in self.cards if c.user_id == user.user_id]
            card = random.choice(user_cards) if user_cards else random.choice(self.cards)

            # Legitimate users consistently reuse 1-2 devices and 1-2 IPs
            device = self.devices[hash(user.user_id) % len(self.devices)]
            ip = self.ips[hash(user.user_id) % len(self.ips)]
            merchant = random.choice(self.merchants)
            address = self.addresses[hash(user.user_id) % len(self.addresses)]

            # Amount: log-normal around merchant avg
            raw_amount = random.lognormvariate(math.log(max(10.0, merchant.avg_amount)), 0.6)
            amount = round(max(1.0, raw_amount), 2)

            transactions.append(
                Transaction(
                    tx_id=tx_id,
                    user_id=user.user_id,
                    card_id=card.card_id,
                    device_id=device.device_id,
                    ip_address=ip.ip_address,
                    merchant_id=merchant.merchant_id,
                    address_id=address.address_id,
                    amount=amount,
                    currency="USD",
                    timestamp=round(t, 2),
                    channel=random.choices(["ONLINE", "MOBILE_APP", "POS"], weights=[0.45, 0.45, 0.10])[0],
                    is_fraud=0,
                    attack_type=AttackType.NONE,
                    fraud_label_delay_days=0,
                    ground_truth_reasons=[],
                )
            )

        transactions.sort(key=lambda x: x.timestamp)
        return transactions
