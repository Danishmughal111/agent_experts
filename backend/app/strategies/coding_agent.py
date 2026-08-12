"""AI Coding Agent — completes real coding projects, delivers to clients.
Generates complete websites, APIs, scripts, extensions etc."""
import json
import os
from datetime import datetime, timezone

from app.strategies.base import BaseStrategy, dec
from app.models import CodingProject
from app.agents import finance


class CodingAgentStrategy(BaseStrategy):
    name = "coding_agent"
    display_name = "AI Coding Agent"
    risk_level = "medium"

    PROJECT_TYPES = ["website", "api", "script", "extension", "automation", "template"]
    LANGUAGES = ["python", "javascript", "typescript", "html", "css", "react", "nextjs"]

    def run(self) -> dict:
        """AI coding agent: analyze what to build → generate code → save project."""
        if not self.can_run():
            return {"status": "skipped", "reason": "Strategy disabled or stop-loss triggered"}

        # Step 1: Decide what coding project to build
        project = self._decide_project()

        # Step 2: Generate complete codebase
        files = self._generate_code(project)

        # Step 3: Save project to disk
        saved = self._save_project(project, files)

        return {
            "status": "completed",
            "project_type": project["type"],
            "title": saved.title,
            "language": saved.language,
            "files_count": len(files),
            "project_id": saved.id,
            "deliverables_ready": True,
            "next_step": "Owner can list this project on freelance platforms or use for client delivery",
        }

    def _decide_project(self) -> dict:
        prompt = (
            "You are a freelance developer looking for coding work. Based on current "
            "market demand for 2025-2026, propose ONE specific coding project to build "
            "that can be sold to clients. Choose from: landing page, REST API, Chrome "
            "extension, automation script, data scraper, SaaS boilerplate, portfolio "
            "website, e-commerce template, dashboard UI, WhatsApp/Telegram bot. "
            "Reply with JSON: {title, type, language, description, target_audience, "
            "estimated_value_usd, complexity (easy/medium/hard)}."
        )
        response = self.ask_ai(prompt)
        return self._parse_json(response, {
            "title": "Modern SaaS Landing Page",
            "type": "website",
            "language": "typescript",
            "description": "A responsive SaaS landing page with Next.js & Tailwind",
            "target_audience": "Startups",
            "estimated_value_usd": 150,
            "complexity": "medium",
        })

    def _generate_code(self, project: dict) -> list:
        """AI generates complete project files."""
        ptype = project.get("type", "website")
        title = project.get("title", "")
        lang = project.get("language", "html")

        prompts = {
            "website": (
                f"Generate COMPLETE, professional, production-ready code for: '{title}'. "
                f"Use {lang}/Next.js with Tailwind CSS. Include:\n"
                f"1. index.html or page.tsx (main page with hero, features, pricing, CTA)\n"
                f"2. styles/css file\n"
                f"3. README.md with setup instructions\n"
                f"Make it look premium, modern, responsive. Use proper HTML5 semantics, "
                f"accessibility attributes. Code must be ready to deploy."
            ),
            "api": (
                f"Generate COMPLETE FastAPI backend for: '{title}'. Include:\n"
                f"1. main.py with routes\n"
                f"2. models.py with database schema\n"
                f"3. requirements.txt\n"
                f"4. README.md with API docs\n"
                f"Make it production-ready with proper error handling."
            ),
            "script": (
                f"Generate a complete Python automation script for: '{title}'. Include:\n"
                f"1. main.py with all logic\n"
                f"2. config.json for settings\n"
                f"3. requirements.txt\n"
                f"4. README.md with usage instructions\n"
                f"Make it robust with error handling and logging."
            ),
            "extension": (
                f"Generate a complete Chrome extension for: '{title}'. Include:\n"
                f"1. manifest.json\n"
                f"2. popup.html + popup.js\n"
                f"3. background.js (if needed)\n"
                f"4. styles.css\n"
                f"5. README.md with installation instructions"
            ),
            "automation": (
                f"Generate a complete automation workflow for: '{title}'. Include:\n"
                f"1. main.py with Selenium/Playwright or API calls\n"
                f"2. config.py\n"
                f"3. requirements.txt\n"
                f"4. README.md\n"
                f"Make it reliable with retry logic and error handling."
            ),
            "template": (
                f"Generate a complete code template/boilerplate for: '{title}'. Include:\n"
                f"1. All necessary project files\n"
                f"2. Config files\n"
                f"3. package.json or requirements.txt\n"
                f"4. README.md\n"
                f"5. Example usage code"
            ),
        }

        prompt = prompts.get(ptype, prompts["website"])
        code = self.ask_ai(prompt, system=(
            "You are a senior software engineer. Write clean, professional, "
            "production-ready code. Use proper naming conventions, comments, "
            "error handling. The code must work immediately after installation. "
            "Output each file with: ### FILE: filename.ext ### as a separator."
        ))

        # Parse files from AI response
        files = []
        current_file = None
        current_content = []

        for line in code.split("\n"):
            if line.startswith("### FILE:") or line.startswith("## File:") or line.startswith("### "):
                if current_file and current_content:
                    files.append({"name": current_file, "content": "\n".join(current_content)})
                # Extract filename
                current_file = line.replace("### FILE:", "").replace("## File:", "").replace("### ", "").strip()
                current_content = []
            else:
                current_content.append(line)

        if current_file and current_content:
            files.append({"name": current_file, "content": "\n".join(current_content)})

        # If no files parsed, create single file
        if not files:
            files = [{"name": "main.py" if lang == "python" else "index.html",
                       "content": code}]

        return files

    def _save_project(self, project: dict, files: list) -> CodingProject:
        cp = CodingProject(
            platform="internal",
            project_type=project.get("type", "website"),
            title=project.get("title", "Coding Project"),
            requirements=project.get("description", ""),
            language=project.get("language", "python"),
            status="delivered",
            deliverables=json.dumps([f["name"] for f in files]),
            budget=dec(project.get("estimated_value_usd", 50)),
        )
        self.db.add(cp)
        self.db.commit()
        self.db.refresh(cp)

        # Save to disk
        project_dir = f"generated_projects/{cp.id}_{self._safe_name(cp.title)}"
        os.makedirs(project_dir, exist_ok=True)

        for f in files:
            file_path = os.path.join(project_dir, f["name"])
            os.makedirs(os.path.dirname(file_path) or project_dir, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as fh:
                fh.write(f["content"])

        cp.github_repo = project_dir
        cp.delivery_url = project_dir
        self.db.commit()

        self.log_execution(
            action="project_built",
            detail=f"Built {cp.project_type}: {cp.title}",
            result=f"{len(files)} files saved to {project_dir}",
        )

        finance.notify(self.db,
            title="💻 Coding Project Ready",
            body=f"'{cp.title}' ({cp.project_type}) is ready. {len(files)} files generated. Can be sold for ${cp.budget}.",
            level="success",
        )
        return cp

    def _safe_name(self, name: str) -> str:
        return "".join(c for c in name[:40] if c.isalnum() or c in " _-").strip() or "project"

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

    def get_all_projects(self) -> list:
        projects = self.db.query(CodingProject).order_by(
            CodingProject.created_at.desc()
        ).all()
        return [
            {
                "id": p.id,
                "title": p.title,
                "type": p.project_type,
                "language": p.language,
                "status": p.status,
                "budget": float(p.budget),
                "github_repo": p.github_repo,
                "client": p.client_name,
            }
            for p in projects
        ]

    def record_client_payment(self, project_id: int, amount: float,
                              client_name: str, payoneer_ref: str = "") -> dict:
        """Record when a client pays for a coding project."""
        project = self.db.query(CodingProject).get(project_id)
        if not project:
            return {"status": "error", "reason": "Project not found"}

        project.status = "paid"
        project.client_name = client_name
        self.db.commit()

        rev = self.record_revenue(
            source_type="coding",
            description=f"Client payment: {project.title}",
            amount=amount,
            platform="freelance",
            external_ref=payoneer_ref,
        )

        finance.deposit(self.db, amount, note=f"Coding project payment: {project.title}")
        finance.notify(self.db,
            title="💸 Client Paid for Coding Project",
            body=f"'{project.title}' — ${amount} received from {client_name}. Check Payoneer.",
            level="success",
        )

        self.log_execution(
            action="client_paid",
            detail=f"Project {project.id}: {client_name} paid ${amount}",
            revenue=amount,
        )
        return {"status": "recorded", "project": project.title, "amount": amount, "client": client_name}