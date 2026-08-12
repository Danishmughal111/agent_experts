"""Business Strategy — AI builds its own business website + acts as business agent.
Marketing, sales, customer support, competitive analysis. Earning through its own business."""
import json
import os
from datetime import datetime, timezone

from app.strategies.base import BaseStrategy, dec
from app.models import BusinessDeal, WebsiteInstance, CodingProject
from app.agents import finance


class BusinessStrategy(BaseStrategy):
    name = "business"
    display_name = "Business Website & Agent"
    risk_level = "low"

    def run(self) -> dict:
        """AI runs business operations: marketing, lead gen, website management."""
        if not self.can_run():
            return {"status": "skipped", "reason": "Strategy disabled or stop-loss triggered"}

        # Step 1: Check if business website exists
        website = self._ensure_website()

        # Step 2: Run marketing outreach
        leads = self._generate_leads()

        # Step 3: Competitive analysis
        analysis = self._competitive_analysis()

        return {
            "status": "completed",
            "website": website.deploy_url or "pending",
            "new_leads": len(leads),
            "competitive_insights": analysis[:200],
            "next_step": "Owner reviews leads, follows up, and closes deals",
        }

    def _ensure_website(self) -> WebsiteInstance:
        """Check/create the agent's business website."""
        existing = self.db.query(WebsiteInstance).first()
        if not existing:
            # AI builds the website
            site = self._build_business_website()
            return site
        return existing

    def _build_business_website(self) -> WebsiteInstance:
        """AI generates the complete business website code."""
        prompt = (
            "Design a complete, professional business website for an AI-powered "
            "freelance agency. The site should sell:\n"
            "- Web development (React, Next.js, Python)\n"
            "- Content writing & SEO\n"
            "- Automation & scripting\n"
            "- Digital products\n\n"
            "Generate the COMPLETE HTML/CSS/JS for a modern, responsive landing page "
            "with:\n"
            "1. Hero section with headline and CTA\n"
            "2. Services section (3-4 services with icons)\n"
            "3. Portfolio/showcase section\n"
            "4. Pricing section\n"
            "5. Contact form\n"
            "6. Footer with social links\n\n"
            "Use Tailwind CSS CDN for styling. Make it production-ready. "
            "Output as: ### FILE: index.html ### [content]"
        )

        code = self.ask_ai(prompt, system=(
            "You are a senior web designer and developer. Create stunning, "
            "conversion-optimized landing pages. Use modern design principles, "
            "proper spacing, and compelling copy that sells services."
        ))

        # Save website files
        site_dir = "generated_business_site"
        os.makedirs(site_dir, exist_ok=True)
        file_path = f"{site_dir}/index.html"

        # Extract HTML content
        html_content = code
        if "### FILE:" in code:
            parts = code.split("### FILE:")[1].split("###", 1)
            html_content = parts[0].replace("index.html", "").strip() + (
                parts[1] if len(parts) > 1 else ""
            )
            html_content = html_content.strip()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html>\n<html lang=\"en\">\n")
            f.write(html_content if html_content.startswith("<") else code)
            if "</html>" not in code:
                f.write("\n</html>")

        site = WebsiteInstance(
            domain="localhost",
            platform="vercel",
            deploy_url=f"file://{os.path.abspath(file_path)}",
            site_type="agency",
            status="active",
        )
        self.db.add(site)
        self.db.commit()
        self.db.refresh(site)

        self.log_execution(
            action="website_built",
            detail="Built business agency website",
            result=f"Saved to {file_path}",
        )

        finance.notify(self.db,
            title="🌐 Business Website Ready",
            body="Your agency website is built! Deploy it to Vercel/Netlify to start getting clients.",
            level="success",
        )
        return site

    def _generate_leads(self) -> list:
        """AI finds potential business leads/clients."""
        prompt = (
            "You are a business development AI. Generate 2-3 realistic business "
            "leads for a tech/freelance agency offering web dev, content, and "
            "automation services. For each lead provide:\n"
            "- Company/name\n"
            "- What they need\n"
            "- Estimated budget\n"
            "- Why they'd be a good fit\n"
            "Reply with JSON list: [{name, company, need, budget_usd, fit_reason, "
            "suggested_approach}]"
        )
        response = self.ask_ai(prompt)
        try:
            text = response.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            leads = json.loads(text)
            if isinstance(leads, list):
                for lead in leads:
                    self._save_business_lead(lead)
                return leads
        except Exception:
            pass
        return []

    def _save_business_lead(self, lead: dict):
        deal = BusinessDeal(
            lead_name=lead.get("name", ""),
            lead_email=lead.get("email", f"{lead.get('name', 'lead').lower().replace(' ', '.')}@example.com"),
            service_type="web_dev",
            requirements=lead.get("need", ""),
            status="lead",
            deal_value=dec(lead.get("budget_usd", 100)),
            notes=lead.get("suggested_approach", ""),
        )
        self.db.add(deal)
        self.db.commit()

    def _competitive_analysis(self) -> str:
        prompt = (
            "Analyze the current competitive landscape for freelance tech agencies "
            "in 2025-2026. What niches are underserved? What pricing strategies work? "
            "What services are in highest demand? Give concise, actionable insights."
        )
        return self.ask_ai(prompt)

    # ---------- Business Deal Management ----------

    def get_pipeline(self) -> list:
        deals = self.db.query(BusinessDeal).order_by(
            BusinessDeal.created_at.desc()
        ).limit(50).all()
        return [
            {
                "id": d.id,
                "name": d.lead_name,
                "email": d.lead_email,
                "service": d.service_type,
                "status": d.status,
                "value": float(d.deal_value),
                "requirements": d.requirements[:100] if d.requirements else "",
                "created": d.created_at.isoformat() if d.created_at else "",
            }
            for d in deals
        ]

    def update_deal_status(self, deal_id: int, new_status: str) -> dict:
        deal = self.db.query(BusinessDeal).get(deal_id)
        if not deal:
            return {"status": "error", "reason": "Deal not found"}

        old_status = deal.status
        deal.status = new_status
        if new_status in ("won", "lost"):
            deal.closed_at = datetime.now(timezone.utc)
        self.db.commit()

        self.log_execution(
            action="deal_updated",
            detail=f"Deal {deal_id}: {old_status} → {new_status}",
        )

        finance.notify(self.db,
            title="🤝 Deal Update",
            body=f"Deal with {deal.lead_name}: {old_status} → {new_status}",
            level="success" if new_status == "won" else "info",
        )
        return {"status": "updated", "deal_id": deal_id, "new_status": new_status}

    def close_won_deal(self, deal_id: int, amount_received: float,
                       payoneer_ref: str = "") -> dict:
        """Record payment from a won business deal."""
        deal = self.db.query(BusinessDeal).get(deal_id)
        if not deal:
            return {"status": "error", "reason": "Deal not found"}

        deal.status = "won"
        deal.closed_at = datetime.now(timezone.utc)
        deal.deal_value = dec(amount_received)
        self.db.commit()

        rev = self.record_revenue(
            source_type="business",
            description=f"Business deal: {deal.lead_name} - {deal.service_type}",
            amount=amount_received,
            platform="direct",
            external_ref=payoneer_ref,
        )

        finance.deposit(self.db, amount_received,
                        note=f"Business deal closed: {deal.lead_name}")
        finance.notify(self.db,
            title="💰 Deal Closed!",
            body=f"${amount_received} received from {deal.lead_name}. Check Payoneer!",
            level="success",
        )

        self.log_execution(
            action="deal_won",
            detail=f"Closed deal with {deal.lead_name}",
            revenue=amount_received,
        )
        return {"status": "won", "deal_id": deal_id, "amount": amount_received}

    # ---------- AI Outreach ----------

    def generate_cold_email(self, lead_name: str, company: str,
                            service: str) -> str:
        """AI writes a cold outreach email."""
        prompt = (
            f"Write a compelling, professional cold email to {lead_name} at "
            f"{company}. We offer: {service} services. Keep it short (100-150 words), "
            f"personalized, value-focused. Include a clear CTA. Make it NOT spammy."
        )
        return self.ask_ai(prompt)

    def generate_social_post(self, topic: str = "") -> str:
        """AI generates social media marketing post."""
        prompt = (
            f"Write an engaging social media post for a tech agency's LinkedIn/Twitter. "
            f"Topic: {topic or 'Why businesses need AI automation in 2025'}. "
            f"Include hashtags, keep it under 280 chars for Twitter or 1000 chars for LinkedIn. "
            f"Make it thought-leadership style."
        )
        return self.ask_ai(prompt)