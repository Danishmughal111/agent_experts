"""Content Monetization Strategy — AI writes, publishes, and monetizes content.
Blogs, articles, social media, with affiliate links and ad revenue."""
import json
from datetime import datetime, timezone

from app.strategies.base import BaseStrategy, dec
from app.models import PublishedContent
from app.agents import finance


class ContentStrategy(BaseStrategy):
    name = "content"
    display_name = "Content Monetization"
    risk_level = "low"

    CONTENT_TYPES = ["blog", "social_post", "newsletter", "video_script", "tutorial"]

    PLATFORMS = ["wordpress", "medium", "blogger", "twitter", "linkedin"]

    AFFILIATE_PROGRAMS = [
        {"name": "Amazon Associates", "category": "general", "commission": "1-10%"},
        {"name": "ShareASale", "category": "various", "commission": "5-30%"},
        {"name": "CJ Affiliate", "category": "various", "commission": "5-25%"},
        {"name": "ClickBank", "category": "digital", "commission": "20-75%"},
        {"name": "Hostinger", "category": "hosting", "commission": "$60-150/sale"},
        {"name": "Bluehost", "category": "hosting", "commission": "$65-130/sale"},
        {"name": "SEMrush", "category": "SEO tools", "commission": "$200/sale"},
        {"name": "Canva Pro", "category": "design", "commission": "$36/sale"},
    ]

    def run(self) -> dict:
        """AI writes content with affiliate links → ready to publish."""
        if not self.can_run():
            return {"status": "skipped", "reason": "Strategy disabled or stop-loss triggered"}

        # Step 1: Pick trending topic
        topic = self._pick_topic()

        # Step 2: Choose affiliate products
        affiliates = self._select_affiliates(topic)

        # Step 3: Write content with embedded affiliate links
        content = self._write_content(topic, affiliates)

        # Step 4: Save content
        saved = self._save_content(topic, content, affiliates)

        return {
            "status": "completed",
            "content_type": saved.content_type,
            "title": saved.title,
            "platform": saved.platform,
            "affiliate_count": len(affiliates),
            "word_count": len(content.split()),
            "content_id": saved.id,
            "ready_to_publish": True,
            "next_step": "Owner publishes on WordPress/Medium with affiliate links and enables ads",
        }

    def _pick_topic(self) -> dict:
        prompt = (
            "Pick ONE trending, high-search-volume topic for a blog post in 2025-2026. "
            "Focus on topics that attract readers with buying intent (affiliate potential). "
            "Categories: tech, making money online, AI tools, SaaS, remote work, productivity, "
            "health tech, personal finance, online business, digital marketing. "
            "Reply with JSON: {title, category, keywords (3-5 comma-separated), "
            "target_audience, content_type (blog/social_post/tutorial), "
            "platform (wordpress/medium/other)}."
        )
        response = self.ask_ai(prompt)
        return self._parse_json(response, {
            "title": "10 Best AI Tools for Small Business in 2025",
            "category": "AI tools",
            "keywords": "AI tools, small business, automation, productivity",
            "target_audience": "Small business owners",
            "content_type": "blog",
            "platform": "wordpress",
        })

    def _select_affiliates(self, topic: dict) -> list:
        prompt = (
            f"Topic: {topic.get('title')}. Category: {topic.get('category')}. "
            f"Target: {topic.get('target_audience')}. "
            f"Available affiliate programs: {json.dumps(self.AFFILIATE_PROGRAMS)}. "
            f"Select 2-3 best affiliate products to recommend in this article. "
            f"Reply with JSON list: [{{program_name, product_name, affiliate_link_placeholder, "
            f"reason_for_recommending}}]."
        )
        response = self.ask_ai(prompt)
        try:
            text = response.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text) if isinstance(json.loads(text), list) else [json.loads(text)]
        except Exception:
            return [
                {"program_name": "Amazon Associates",
                 "product_name": "Relevant product",
                 "affiliate_link_placeholder": "https://amzn.to/YOUR_AFFILIATE_ID",
                 "reason_for_recommending": "High trust platform, broad product range"},
            ]

    def _write_content(self, topic: dict, affiliates: list) -> str:
        aff_text = "\n".join(
            f"- {a['program_name']}: {a.get('product_name', '')} ({a.get('reason_for_recommending', '')})"
            for a in affiliates
        )

        prompt = (
            f"Write a HIGH-QUALITY, SEO-optimized blog post:\n"
            f"Title: {topic.get('title')}\n"
            f"Keywords: {topic.get('keywords')}\n"
            f"Audience: {topic.get('target_audience')}\n\n"
            f"Affiliate products to naturally integrate:\n{aff_text}\n\n"
            f"Guidelines:\n"
            f"- 1500-2500 words\n"
            f"- Engaging introduction with hook\n"
            f"- Use H2/H3 subheadings\n"
            f"- Include numbered lists and bullet points\n"
            f"- Naturally mention affiliate products with placeholder links [AFFILIATE_LINK]\n"
            f"- End with a call-to-action\n"
            f"- SEO meta description at the top (in a comment)\n"
            f"- Make it valuable and actionable\n\n"
            f"Write the COMPLETE article now."
        )
        return self.ask_ai(prompt, system=(
            "You are a professional content writer and SEO expert. Write engaging, "
            "valuable content that ranks on Google and converts readers. Use natural "
            "language, avoid keyword stuffing. Make readers want to click affiliate links."
        ))

    def _save_content(self, topic: dict, content: str, affiliates: list) -> PublishedContent:
        pc = PublishedContent(
            platform=topic.get("platform", "wordpress"),
            title=topic.get("title", "Blog Post"),
            content_type=topic.get("content_type", "blog"),
            affiliate_links=json.dumps(affiliates),
            views=0,
            clicks=0,
        )
        self.db.add(pc)
        self.db.commit()
        self.db.refresh(pc)

        # Save content to file
        import os
        os.makedirs("generated_content", exist_ok=True)
        safe_title = "".join(c for c in topic.get("title", "content")[:50] if c.isalnum() or c in " _-")
        file_path = f"generated_content/{pc.id}_{safe_title}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {topic.get('title')}\n\n")
            f.write(f"> Category: {topic.get('category')} | Keywords: {topic.get('keywords')}\n\n")
            f.write(f"## Affiliate Products\n\n")
            for a in affiliates:
                f.write(f"- **{a['program_name']}**: {a.get('product_name', '')}\n")
            f.write("\n---\n\n")
            f.write(content)

        pc.url = file_path
        self.db.commit()

        self.log_execution(
            action="content_created",
            detail=f"Wrote {topic.get('content_type')}: {topic.get('title')}",
            result=f"{len(content.split())} words, {len(affiliates)} affiliate products",
        )

        finance.notify(self.db,
            title="📝 Content Ready to Publish",
            body=f"'{topic.get('title')}' ({len(content.split())} words) with {len(affiliates)} affiliate links is ready.",
            level="info",
        )
        return pc

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

    def get_all_content(self) -> list:
        content = self.db.query(PublishedContent).order_by(
            PublishedContent.published_at.desc()
        ).all()
        return [
            {
                "id": c.id,
                "title": c.title,
                "platform": c.platform,
                "content_type": c.content_type,
                "views": c.views,
                "clicks": c.clicks,
                "revenue": float(c.revenue),
                "url": c.url,
            }
            for c in content
        ]

    def record_views(self, content_id: int, views: int = 0, clicks: int = 0) -> dict:
        """Update view/click stats."""
        content = self.db.query(PublishedContent).get(content_id)
        if not content:
            return {"status": "error", "reason": "Not found"}
        content.views = (content.views or 0) + views
        content.clicks = (content.clicks or 0) + clicks
        self.db.commit()
        return {"status": "ok", "views": content.views, "clicks": content.clicks}

    def record_revenue_from_content(self, content_id: int, amount: float,
                                     source: str = "") -> dict:
        """Record ad/affiliate revenue from content."""
        content = self.db.query(PublishedContent).get(content_id)
        if not content:
            return {"status": "error", "reason": "Not found"}

        content.revenue = dec((content.revenue or 0) + amount)
        self.db.commit()

        rev = self.record_revenue(
            source_type="content_affiliate" if "affiliate" in source.lower() else "content_ad",
            description=f"Content revenue: {content.title}",
            amount=amount,
            platform=content.platform,
        )

        finance.deposit(self.db, amount, note=f"Content revenue: {content.title}")
        finance.notify(self.db,
            title="📈 Content Revenue!",
            body=f"${amount} earned from '{content.title}' via {source}",
            level="success",
        )
        self.log_execution(
            action="content_revenue",
            detail=f"Content {content_id}: ${amount} from {source}",
            revenue=amount,
        )
        return {"status": "recorded", "content": content.title, "amount": amount}