"""Fictional vendor templates for the demo dataset.

Deliberately fictional company names (not real fintech/telco/cloud
providers) even though the categories are drawn from the real Nigerian
fintech ecosystem (payment processors, KYC/AML providers, cloud hosts,
telco partners, open-banking aggregators) -- this system generates
fabricated CVEs, breach histories, and risk scores per vendor, and
attributing that fabricated data to real, identifiable companies would be
inappropriate regardless of intent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VendorTemplate:
    name: str
    legal_entity_name: str
    industry: str
    country: str = "NG"


VENDOR_TEMPLATES: tuple[VendorTemplate, ...] = (
    VendorTemplate("NairaSwitch Processing", "NairaSwitch Processing Ltd", "Payment_Processor"),
    VendorTemplate("FlowRails Payments", "FlowRails Payments Ltd", "Payment_Gateway"),
    VendorTemplate("PayCore Gateway Services", "PayCore Gateway Services Ltd", "Payment_Gateway"),
    VendorTemplate("IDVerix Identity Solutions", "IDVerix Identity Solutions Ltd", "KYC_AML"),
    VendorTemplate("ClearFace Biometrics Africa", "ClearFace Biometrics Africa Ltd", "KYC_AML"),
    VendorTemplate("TrustLayer Compliance Tech", "TrustLayer Compliance Technologies Ltd", "KYC_AML"),
    VendorTemplate("CoreLine Cloud Services", "CoreLine Cloud Services Ltd", "Cloud_Infra"),
    VendorTemplate("DataVault Centre Systems", "DataVault Centre Systems Ltd", "Cloud_Infra"),
    VendorTemplate("NimbusCloud Africa", "NimbusCloud Africa Ltd", "Cloud_Infra"),
    VendorTemplate("CellLink Business Connect", "CellLink Business Connect Ltd", "Telco_Partner"),
    VendorTemplate("SkyTel Enterprise Solutions", "SkyTel Enterprise Solutions Ltd", "Telco_Partner"),
    VendorTemplate("GlobalWave Business Services", "GlobalWave Business Services Ltd", "Telco_Partner"),
    VendorTemplate("LinkBank Open Banking", "LinkBank Open Banking Ltd", "Open_Banking_Aggregator"),
    VendorTemplate("BranchLink Data Connect", "BranchLink Data Connect Ltd", "Open_Banking_Aggregator"),
    VendorTemplate("MeshPay Africa Aggregation", "MeshPay Africa Aggregation Ltd", "Open_Banking_Aggregator"),
    VendorTemplate("PingRoute Messaging Gateway", "PingRoute Messaging Gateway Ltd", "Notification_Services"),
    VendorTemplate("WalletForge Infrastructure", "WalletForge Infrastructure Ltd", "Payment_Processor"),
    VendorTemplate("CoreBanc BaaS Platform", "CoreBanc BaaS Platform Ltd", "Banking_as_a_Service"),
    VendorTemplate("MerchantEdge Payment Services", "MerchantEdge Payment Services Ltd", "Payment_Gateway"),
)

DEMO_VENDOR = VendorTemplate("Demo Critical Vendor (left-pad)", "Demo Critical Vendor Ltd", "Payment_Processor")
