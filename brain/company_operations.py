"""Operational registry for AION's specialist departments.

This is deliberately not a fictional cast of agents.  Every department is
bound to code and a scheduled workflow that can be inspected in the project.
The registry is used to detect a broken hand-off before it is presented as an
active part of the company.
"""

from pathlib import Path


class CompanyOperations:
    DEPARTMENTS = (
        ("research", ("brain/autonomous_inquiry.py", "brain/research_to_story.py"),
         (".github/workflows/autonomous-inquiry.yml", ".github/workflows/research-to-story.yml")),
        ("story", ("brain/creator_autonomy.py", "brain/creator_series.py"),
         (".github/workflows/creator-autonomy.yml", ".github/workflows/render-creator-library.yml")),
        ("costume", ("brain/costume_direction.py", "tools/build_costume_briefs.py"),
         (".github/workflows/costume-briefs.yml",)),
        ("visual", ("brain/visual_content.py", "brain/creator_scene_production.py", "tools/image_render.py"),
         (".github/workflows/instagram-cycle.yml", ".github/workflows/reel-cycle.yml", ".github/workflows/creator-scene-production.yml")),
        ("audio", ("tools/voice.py", "tools/reel_render.py"),
         (".github/workflows/reel-cycle.yml",)),
        ("quality", ("brain/youtube_quality.py", "brain/video_quality.py", "brain/evidence_qualification.py"),
         (".github/workflows/tests.yml",)),
        ("publishing", ("brain/reels.py", "brain/youtube_creator_queue.py", "tools/youtube.py"),
         (".github/workflows/reel-cycle.yml", ".github/workflows/instagram-cycle.yml", ".github/workflows/youtube-creator.yml")),
        ("growth", ("brain/social_feedback.py", "brain/growth_pulse.py"),
         (".github/workflows/instagram-feedback.yml", ".github/workflows/growth-pulse.yml")),
        ("memory", ("brain/memory.py", "brain/asset_hygiene.py"),
         (".github/workflows/asset-hygiene.yml", ".github/workflows/obsidian-brain.yml")),
        ("engineering", ("brain/system_reliability.py", "brain/company_quality_audit.py"),
         (".github/workflows/system-reliability.yml", ".github/workflows/tests.yml")),
        ("cyber-guard", ("brain/cyber_guard.py", "tools/run_cyber_guard.py"),
         (".github/workflows/cyber-guard.yml",)),
        ("evolution-lab", ("brain/evolution_lab.py", "brain/evolution.py", "brain/experiment_runner.py"),
         (".github/workflows/evolution-cycle.yml", ".github/workflows/experiment-runner.yml")),
    )

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def audit(self):
        results = []
        for department, modules, workflows in self.DEPARTMENTS:
            missing = [item for item in (*modules, *workflows) if not (self.root / item).is_file()]
            results.append({
                "id": department,
                "modules": list(modules),
                "workflows": list(workflows),
                "status": "operational" if not missing else "blocked",
                "missing": missing,
            })
        return {
            "status": "operational" if all(item["status"] == "operational" for item in results) else "blocked",
            "departments": results,
        }
