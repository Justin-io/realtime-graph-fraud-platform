"""Data models for multi-entity graph simulation and financial transactions."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AttackType(str, Enum):
    NONE = "NONE"
    VELOCITY_BURST = "VELOCITY_BURST"
    DEVICE_SHARING_RING = "DEVICE_SHARING_RING"
    IMPOSSIBLE_TRAVEL = "IMPOSSIBLE_TRAVEL"
    IP_PROXY_CLUSTER = "IP_PROXY_CLUSTER"
    MERCHANT_COLLUSION = "MERCHANT_COLLUSION"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"


class User(BaseModel):
    user_id: str
    name: str
    signup_timestamp: float
    kyc_level: int = 1  # 1: Basic, 2: Verified, 3: Full Enterprise
    account_age_days: float = 30.0
    base_risk: float = 0.05


class Card(BaseModel):
    card_id: str
    user_id: str
    card_brand: str  # Visa, Mastercard, Amex
    card_type: str   # Credit, Debit, Prepaid
    issuer_country: str = "US"
    created_timestamp: float


class Device(BaseModel):
    device_id: str
    os_name: str     # iOS, Android, Windows, macOS, Linux
    browser_name: str # Chrome, Safari, Firefox, Edge
    is_emulator: bool = False
    is_rooted: bool = False
    fingerprint_hash: str


class IPAddress(BaseModel):
    ip_address: str
    asn: int
    country: str = "US"
    is_vpn: bool = False
    is_tor: bool = False
    is_datacenter: bool = False
    latitude: float = 40.7128
    longitude: float = -74.0060


class Merchant(BaseModel):
    merchant_id: str
    merchant_name: str
    mcc_code: str    # Merchant Category Code (e.g. 5411 Grocery, 5732 Electronics, 7995 Gambling)
    risk_tier: str = "STANDARD"  # LOW, STANDARD, HIGH_RISK
    avg_amount: float = 85.0


class Address(BaseModel):
    address_id: str
    street: str
    city: str
    country: str = "US"
    postal_code: str
    is_po_box: bool = False
    latitude: float = 40.7128
    longitude: float = -74.0060


class Transaction(BaseModel):
    tx_id: str
    user_id: str
    card_id: str
    device_id: str
    ip_address: str
    merchant_id: str
    address_id: str
    amount: float
    currency: str = "USD"
    timestamp: float
    channel: str = "ONLINE"  # ONLINE, MOBILE_APP, POS, CONTACTLESS
    is_fraud: int = 0  # 0: Legitimate, 1: Fraudulent
    attack_type: AttackType = AttackType.NONE
    fraud_label_delay_days: int = 0
    ground_truth_reasons: List[str] = Field(default_factory=list)
