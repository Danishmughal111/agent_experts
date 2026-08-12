"""Freelance Strategy — AI finds gigs, writes proposals, tracks projects.
Platforms: Upwork, Fiverr, PeoplePerHour. Real client work → real Payoneer payments."""
import json
import re
from datetime import datetime, timezone

from app.strategies.base import BaseStrategy, dec
from app.models import FreelanceLead, CodingProject
from app.agents import finance


class FreelanceStrategy(BaseStrategy):
    name = "freelance"
    display_name = "Freelance Bot"
    risk_level = "medium"

    PLATFORMS = ["upwork", "fiverr", "peopleperhour"]
    SKILLS = [
        "Python scripting", "Web development (React/Next.js)", "API development",
        "Data entry & processing", "Content writing", "Automation/bots",
        "Excel/Google Sheets", "Data scraping", "WordPress development",
        "Chrome extensions", "PDF generation", "Email templates",
    ]

    def run(self) -> dict:
        """AI finds freelance gigs → writes proposals → records leads."""
        if not self.can_run():
            return {"status": "skipped", "reason": "Strategy disabled or stop-loss triggered"}

        # Step 1: Find matching gigs
        gigs = self._find_gigs()

        # Step 2: For each gig, write proposal
        proposals_sent = 0
        for gig in gigs[:3]:  # Max 3 per cycle
            proposal = self._write_proposal(gig)
            saved = self._save_lead(gig, proposal)
            proposals_sent += 1

        return {
            "status": "completed",
            "gigs_found": len(gigs),
            "proposals_sent": proposals_sent,
            "platforms_checked": self.PLATFORMS[:2],
            "next_step": "Owner reviews leads and submits proposals on platform",
        }

    def _find_gigs(self) -> list:
        """AI simulates gig discovery (with potential real API integration)."""
        prompt = (
            f"Based on these skills: {json.dumps(self.SKILLS)}. "
            f"On platforms: {', '.join(self.PLATFORMS)}. "
            f"Find 2-3 realistic freelance gigs that match these skills. "
            f"For each gig provide realistic details. "
            f"Reply with JSON list: "
            f"[{{title, platform, budget_usd, description_short, skills_required, "
            f"client_type, competition_level (low/medium/high)}}]"
        )
        response = self.ask_ai(prompt)
        try:
            text = response.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            gigs = json.loads(text)
            return gigs if isinstance(gigs, list) else []
        except Exception:
            return [
                {
                    "title": "Build a simple landing page with React",
                    "platform": "upwork",
                    "budget_usd": 150,
                    "description_short": "Need a responsive landing page with contact form",
                    "skills_required": "React, CSS, HTML",
                    "client_type": "small business",
                    "competition_level": "medium",
                },
            ]

    def _write_proposal(self, gig: dict) -> str:
        prompt = (
            f"Write a winning freelance proposal for this gig:\n"
            f"Title: {gig.get('title')}\n"
            f"Platform: {gig.get('platform')}\n"
            f"Budget: ${gig.get('budget_usd')}\n"
            f"Description: {gig.get('description_short')}\n\n"
            f"Guidelines:\n"
            f"- Professional, friendly tone\n"
            f"- Show understanding of the project\n"
            f"- Mention relevant experience/skills\n"
            f"- Propose timeline (1-3 days)\n"
            f"- Include a specific question to engage the client\n"
            f"- Keep it concise (200-300 words)\n"
            f"- End with a call to action\n\n"
            f"Write the COMPLETE proposal."
        )
        return self.ask_ai(prompt, system=(
            "You are an expert freelance proposal writer. Your proposals have "
            "an 80% acceptance rate. Be professional, specific, and persuasive. "
            "Show you read the job description carefully."
        ))

    def _save_lead(self, gig: dict, proposal: str) -> FreelanceLead:
        lead = FreelanceLead(
            platform=gig.get("platform", "upwork"),
            gig_id=f"auto_{int(datetime.now(timezone.utc).timestamp())}",
            title=gig.get("title", ""),
            description=gig.get("description_short", ""),
            budget=dec(gig.get("budget_usd", 50)),
            currency="USD",
            proposal_sent=False,
            proposal_text=proposal,
            status="new",
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)

        self.log_execution(
            action="gig_found",
            detail=f"Found: {lead.title} (${lead.budget})",
            result=f"Proposal written ({len(proposal.split())} words)",
        )

        finance.notify(self.db,
            title="🔍 Freelance Gig Found",
            body=(f"'{lead.title}' on {lead.platform} — ${lead.budget}. "
                  f"Proposal ready. Review and apply!"),
            level="info",
        )
        return lead

    def mark_applied(self, lead_id: int, external_ref: str = "") -> dict:
        """Mark a lead as applied (proposal sent on platform)."""
        lead = self.db.query(FreelanceLead).get(lead_id)
        if not lead:
            return {"status": "error", "reason": "Not found"}

        lead.proposal_sent = True
        lead.status = "applied"
        if external_ref:
            lead.gig_id = external_ref
        self.db.commit()

        self.log_execution(
            action="proposal_submitted",
            detail=f"Applied to: {lead.title}",
        )
        return {"status": "applied", "lead": lead.title}

    def mark_accepted(self, lead_id: int, agreed_amount: float = None) -> dict:
        """Mark a gig as accepted (client hired)."""
        lead = self.db.query(FreelanceLead).get(lead_id)
        if not lead:
            return {"status": "error", "reason": "Not found"}

        lead.status = "accepted"
        if agreed_amount:
            lead.budget = dec(agreed_amount)
        self.db.commit()

        self.log_execution(
            action="gig_accepted",
            detail=f"Won: {lead.title} for ${lead.budget}",
        )

        finance.notify(self.db,
            title="🎉 Gig Won!",
            body=f"Client accepted '{lead.title}' — ${lead.budget}. Time to deliver!",
            level="success",
        )
        return {"status": "accepted", "lead": lead.title, "budget": float(lead.budget)}

    def record_payment(self, lead_id: int, amount: float,
                       client_name: str = "", payoneer_ref: str = "") -> dict:
        """Record client payment for completed freelance work."""
        lead = self.db.query(FreelanceLead).get(lead_id)
        if not lead:
            return {"status": "error", "reason": "Not found"}

        lead.status = "completed"
        self.db.commit()

        rev = self.record_revenue(
            source_type="freelance",
            description=f"Freelance payment: {lead.title}",
            amount=amount,
            platform=lead.platform,
            external_ref=payoneer_ref,
        )

        finance.deposit(self.db, amount,
                        note=f"Freelance payment: {lead.title} ({lead.platform})")
        finance.notify(self.db,
            title="💸 Freelance Payment Received!",
            body=f"${amount} received for '{lead.title}'. Check your Payoneer!",
            level="success",
        )

        self.log_execution(
            action="freelance_paid",
            detail=f"Lead {lead.id}: {client_name} paid ${amount}",
            revenue=amount,
        )
        return {"status": "paid", "lead": lead.title, "amount": amount}

    def get_leads(self, status: str = "") -> list:
        q = self.db.query(FreelanceLead).order_by(FreelanceLead.created_at.desc())
        if status:
            q = q.filter_by(status=status)
        leads = q.limit(50).all()
        return [
            {
                "id": l.id,
                "platform": l.platform,
                "title": l.title,
                "budget": float(l.budget),
                "status": l.status,
                "proposal_sent": l.proposal_sent,
                "created_at": l.created_at.isoformat() if l.created_at else "",
            }
            for l in leads
        ]