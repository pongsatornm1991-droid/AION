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
         (".github/workflows/creator-autonomy.yml", ".github/workflows/assemble-creator-episode.yml")),
        ("costume", ("brain/costume_direction.py", "tools/build_costume_briefs.py"),
         (".github/workflows/costume-briefs.yml",)),
        ("visual", ("brain/visual_content.py", "brain/creator_scene_production.py", "tools/image_render.py"),
         (".github/workflows/instagram-cycle.yml", ".github/workflows/reel-cycle.yml", ".github/workflows/creator-scene-production.yml")),
        ("audio", ("tools/voice.py", "tools/reel_render.py", "tools/assemble_creator_episode.py"),
         (".github/workflows/assemble-creator-episode.yml", ".github/workflows/reel-cycle.yml")),
        ("quality", ("brain/youtube_quality.py", "brain/video_quality.py", "brain/evidence_qualification.py"),
         (".github/workflows/tests.yml",)),
        ("publishing", ("brain/reels.py", "brain/youtube_creator_queue.py", "tools/youtube.py"),
         (".github/workflows/reel-cycle.yml", ".github/workflows/instagram-cycle.yml", ".github/workflows/youtube-creator.yml", ".github/workflows/youtube-longform.yml")),
        ("growth", ("brain/social_feedback.py", "brain/growth_pulse.py"),
         (".github/workflows/instagram-feedback.yml", ".github/workflows/growth-pulse.yml")),
        ("audience-accessibility", ("brain/audience_accessibility.py", "brain/youtube_audience.py", "brain/youtube_quality.py"),
         (".github/workflows/audience-accessibility.yml", ".github/workflows/youtube-audience.yml", ".github/workflows/youtube-creator.yml")),
        ("social-intelligence", ("brain/social_intelligence.py", "brain/content_router.py"),
         (".github/workflows/growth-pulse.yml", ".github/workflows/content-experiment-evaluator.yml")),
        ("admin-operations", ("brain/admin_operations.py", "brain/company_work_registry.py"),
         # The health publisher observes this department; including it here
         # would make the dashboard report this department as "running" while
         # the publisher is merely writing its own read-only snapshot.
         (".github/workflows/admin-operations.yml",)),
        ("memory", ("brain/memory.py", "brain/asset_hygiene.py"),
         (".github/workflows/asset-hygiene.yml", ".github/workflows/obsidian-brain.yml")),
        ("engineering", ("brain/system_reliability.py", "brain/company_quality_audit.py"),
         (".github/workflows/system-reliability.yml", ".github/workflows/tests.yml")),
        ("cyber-guard", ("brain/cyber_guard.py", "tools/run_cyber_guard.py"),
         (".github/workflows/cyber-guard.yml",)),
        ("evolution-lab", ("brain/evolution_lab.py", "brain/evolution.py", "brain/experiment_runner.py"),
         (".github/workflows/evolution-cycle.yml", ".github/workflows/experiment-runner.yml")),
        ("science-lab", ("brain/scientific_discovery.py", "tools/run_scientific_discovery.py"),
         (".github/workflows/scientific-discovery.yml",)),
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
