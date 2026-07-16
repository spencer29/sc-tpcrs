"""Demo user definitions for local/dev seeding.

Every demo user shares the same password so graders/reviewers don't need to
track 8 separate credentials -- this is explicitly a dev/demo convenience,
never used outside ENV=development (see routers/auth.py's dev-only guard).
"""

from __future__ import annotations

from dataclasses import dataclass

DEMO_PASSWORD = "Demo1234!"


@dataclass(frozen=True)
class DemoUser:
    email: str
    full_name: str
    role: str


DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser("risk.officer1@sc-tpcrs.demo", "Amaka Okafor", "risk_officer"),
    DemoUser("risk.officer2@sc-tpcrs.demo", "Chinedu Balogun", "risk_officer"),
    DemoUser("compliance1@sc-tpcrs.demo", "Ifeoma Nwosu", "compliance_manager"),
    DemoUser("compliance2@sc-tpcrs.demo", "Tunde Adeyemi", "compliance_manager"),
    DemoUser("ciso1@sc-tpcrs.demo", "Ngozi Eze", "ciso"),
    DemoUser("ciso2@sc-tpcrs.demo", "Segun Adebayo", "ciso"),
    DemoUser("admin1@sc-tpcrs.demo", "Yusuf Bello", "admin"),
    DemoUser("admin2@sc-tpcrs.demo", "Grace Umeh", "admin"),
)
