"""Digital Products Strategy — AI creates and sells on Gumroad.
Real products, real listings, real money via Gumroad → Payoneer."""
import json
import os
from datetime import datetime, timezone

from app.strategies.base import BaseStrategy, dec
from app.models import DigitalProduct
from app.agents import finance


class DigitalProductsStrategy(BaseStrategy):
    name = "digital_products"
    display_name = "Digital Products (Gumroad)"
    risk_level = "low"

    PRODUCT_TYPES = ["ebook", "template", "course_outline", "code_snippet",
                     "design_asset", "canva_template", "checklist", "guide",
                     "spreadsheet_template", "social_media_pack"]

    def run(self) -> dict:
        """AI decides what digital product to create, generates it, and
        prepares for Gumroad listing. Owner uploads to Gumroad manually
        or via Gumroad API if configured."""
        if not self.can_run():
            return {"status": "skipped", "reason": "Strategy disabled or stop-loss triggered"}

        # Step 1: AI analyzes market trends for best product ideas
        market_analysis = self._analyze_market()

        # Step 2: Pick best product to create
        product = self._pick_best_product(market_analysis)

        # Step 3: Generate the product content
        content = self._generate_product(product)

        # Step 4: Save + create DB record
        saved = self._save_and_record(product, content)

        # Step 5: Propose pricing
        pricing = self._recommend_pricing(product)

        return {
            "status": "completed",
            "product_type": product["type"],
            "title": saved.title,
            "description": product.get("description", "")[:200],
            "price_recommendation": f"${pricing['price']}",
            "listing_ready": True,
            "next_step": "Owner lists this product on Gumroad and sets Payoneer as payout method",
            "product_id": saved.id,
        }

    def _analyze_market(self) -> str:
        prompt = (
            "Analyze trending digital product categories for 2025-2026 that sell "
            "well on Gumroad. What types of digital products have high demand and "
            "low competition? Focus on products an AI can create: eBooks, templates, "
            "guides, checklists, code snippets, Canva templates, spreadsheet templates. "
            "List top 3 categories with brief reasoning."
        )
        return self.ask_ai(prompt)

    def _pick_best_product(self, market_analysis: str) -> dict:
        prompt = (
            f"Market analysis: {market_analysis}\n\n"
            f"Choose ONE specific digital product the AI should create right now. "
            f"Pick from these types: {', '.join(self.PRODUCT_TYPES)}. "
            f"Reply with JSON: {{title, type, description_short, target_audience, file_format}}."
        )
        response = self.ask_ai(prompt)
        return self._parse_json(response, {
            "title": "AI-Generated Business Toolkit",
            "type": "guide",
            "description_short": "A comprehensive guide for small business owners",
            "target_audience": "entrepreneurs",
            "file_format": "PDF",
        })

    def _generate_product(self, product: dict) -> str:
        """AI generates the actual product content."""
        ptype = product.get("type", "guide")
        title = product.get("title", "Digital Product")

        prompt = (
            f"Create a high-quality, valuable {ptype}: '{title}'. "
            f"For target: {product.get('target_audience', 'general audience')}. "
            f"Format: {product.get('file_format', 'PDF/text')}. "
            f"Make it detailed, professional, and ready to sell. "
            f"Include: title page, table of contents, main content (at least 5 "
            f"sections), actionable tips, and a conclusion. "
            f"Write the COMPLETE product content."
        )
        content = self.ask_ai(prompt, system=(
            "You are a professional digital product creator. Your content is "
            "valuable, well-structured, and ready to sell on Gumroad. Write in "
            "clear, professional language. Include practical examples."
        ))
        return content

    def _save_and_record(self, product: dict, content: str) -> DigitalProduct:
        dp = DigitalProduct(
            title=product.get("title", "Digital Product"),
            description=product.get("description_short", "")[:500],
            product_type=product.get("type", "guide"),
            platform="gumroad",
            price=dec(9.99),  # initial price, AI recommends later
            status="draft",
            file_path="generated_products/",
        )
        self.db.add(dp)
        self.db.commit()
        self.db.refresh(dp)

        # Save content to file
        os.makedirs("generated_products", exist_ok=True)
        safe_name = "".join(c for c in product.get("title", "product")[:50] if c.isalnum() or c in " _-")
        file_path = f"generated_products/{dp.id}_{safe_name}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {product.get('title')}\n")
            f.write(f"Type: {product.get('type')}\n")
            f.write(f"Created: {datetime.now(timezone.utc).isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            f.write(content)

        dp.file_path = file_path
        dp.status = "listed"
        self.db.commit()

        self.log_execution(
            action="product_created",
            detail=f"Created {dp.product_type}: {dp.title}",
            result=f"Product ID {dp.id} ready for Gumroad listing",
        )
        return dp

    def _recommend_pricing(self, product: dict) -> dict:
        prompt = (
            f"Product: {product.get('title')}, type: {product.get('type')}. "
            f"Target: {product.get('target_audience', 'general')}. "
            f"Recommend a price in USD for Gumroad. Consider competitor pricing. "
            f"Reply with JSON: {{price, currency, reasoning_short}}."
        )
        response = self.ask_ai(prompt)
        prices = {
            "ebook": 14.99, "template": 9.99, "course_outline": 24.99,
            "code_snippet": 7.99, "design_asset": 12.99,
            "canva_template": 8.99, "checklist": 5.99,
            "guide": 15.99, "spreadsheet_template": 11.99,
            "social_media_pack": 19.99,
        }
        return self._parse_json(response, {
            "price": prices.get(product.get("type", "guide"), 9.99),
            "currency": "USD",
            "reasoning_short": "Competitive pricing for Gumroad marketplace",
        })

    def _parse_json(self, text: str, default: dict) -> dict:
        try:
            text = text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except (json.JSONDecodeError, Exception):
            return default

    def get_all_products(self) -> list:
        products = self.db.query(DigitalProduct).order_by(
            DigitalProduct.created_at.desc()
        ).all()
        return [
            {
                "id": p.id,
                "title": p.title,
                "type": p.product_type,
                "price": float(p.price),
                "status": p.status,
                "sales_count": p.sales_count,
                "total_revenue": float(p.total_revenue),
                "platform": p.platform,
            }
            for p in products
        ]

    def record_sale(self, product_id: int, amount: float, gumroad_ref: str = "") -> dict:
        """Record a real Gumroad sale + update Payoneer tracking."""
        product = self.db.query(DigitalProduct).get(product_id)
        if not product:
            return {"status": "error", "reason": "Product not found"}

        product.sales_count = (product.sales_count or 0) + 1
        product.total_revenue = dec((product.total_revenue or 0) + amount)
        self.db.commit()

        rev = self.record_revenue(
            source_type="digital_product",
            description=f"Gumroad sale: {product.title}",
            amount=amount,
            platform="gumroad",
            external_ref=gumroad_ref,
        )

        finance.deposit(self.db, amount, note=f"Digital product sale: {product.title}")
        finance.notify(self.db,
            title="💰 Product Sold!",
            body=f"'{product.title}' sold for ${amount} on Gumroad. Check Payoneer.",
            level="success",
        )

        self.log_execution(
            action="product_sold",
            detail=f"Product {product.id}: {product.title}",
            revenue=amount,
        )
        return {"status": "recorded", "product": product.title, "amount": amount}