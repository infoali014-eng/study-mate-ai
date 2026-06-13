from datetime import date, timedelta

from modules import ai_engine


def _ask_selected_ai(prompt, model=None):
    """Use the selected AI provider, with a fallback for older loaded modules."""
    if hasattr(ai_engine, "ask_ai"):
        return ai_engine.ask_ai(prompt, model=model)
    return ai_engine.ask_ollama(prompt, model=model)


def _days_until_exam(exam_date):
    """Return at least one planning day, even if the exam date is today."""
    return max(1, (exam_date - date.today()).days + 1)


def _fallback_revision_plan(
    subject_name,
    exam_date,
    preparation_level,
    confidence_level,
    weak_topics,
):
    """Create a simple local plan if Ollama is unavailable."""
    total_days = _days_until_exam(exam_date)
    topics = weak_topics or ["core concepts", "important definitions", "practice questions"]
    plan_lines = []

    for day_number in range(1, total_days + 1):
        plan_date = date.today() + timedelta(days=day_number - 1)
        topic = topics[(day_number - 1) % len(topics)]
        task = (
            f"Revise {topic}, make short notes, and test yourself with active recall."
        )

        if preparation_level <= 4 or confidence_level <= 4:
            task += " Spend extra time on basics before attempting questions."
        elif preparation_level >= 8 and confidence_level >= 8:
            task += " Focus on timed practice and quick revision."

        plan_lines.append(
            f"Day {day_number} - {plan_date.strftime('%d %b %Y')}: {task}"
        )

    return "\n".join(plan_lines)


def generate_revision_plan(
    subject_name,
    exam_date,
    preparation_level,
    confidence_level,
    weak_topics,
    model=None,
):
    """Generate a day-wise study plan using the selected AI provider."""
    total_days = _days_until_exam(exam_date)
    weak_topic_text = ", ".join(weak_topics) if weak_topics else "No weak topics selected"

    prompt = f"""
You are StudyMate AI, an offline study planner for students.
Create a practical day-wise revision plan.

Subject: {subject_name}
Today: {date.today().isoformat()}
Exam date: {exam_date.isoformat()}
Total planning days: {total_days}
Preparation level out of 10: {preparation_level}
Confidence level out of 10: {confidence_level}
Weak topics: {weak_topic_text}

Rules:
- Make one section per day.
- Include revision, practice, and quick review.
- Give more time to weak topics.
- Keep the plan realistic for a student.
- Do not include motivational filler.
"""

    try:
        plan_text = _ask_selected_ai(prompt, model=model)
    except Exception:
        plan_text = _fallback_revision_plan(
            subject_name=subject_name,
            exam_date=exam_date,
            preparation_level=preparation_level,
            confidence_level=confidence_level,
            weak_topics=weak_topics,
        )

    return plan_text


def build_revision_plan(subject_name, days=7):
    """Compatibility helper used by older planner code."""
    today = date.today()
    plan = []

    for day in range(days):
        plan.append(
            {
                "date": today + timedelta(days=day),
                "task": f"Revise {subject_name} notes and practice active recall.",
            }
        )

    return plan
