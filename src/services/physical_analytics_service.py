from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Sequence


EXERCISES = (
    "curl_up",
    "push_up",
    "sit_and_reach",
    "walk_600m",
    "dash_50m",
    "bow_hold",
    "plank",
)


class PhysicalAnalyticsService:
    @staticmethod
    def calculate(results_payload: Sequence[Dict[str, Any]]) -> Dict[str, object]:
        if not results_payload:
            return PhysicalAnalyticsService._empty_response()

        exercise_totals: Dict[str, float] = defaultdict(float)
        exercise_counts: Dict[str, int] = defaultdict(int)

        student_totals: Dict[str | int, float] = defaultdict(float)
        student_counts: Dict[str | int, int] = defaultdict(int)
        student_names: Dict[str | int, str] = {}

        for idx, result in enumerate(results_payload):
            student_identifier: str | int | None = result.get("student_id")
            if student_identifier is None:
                student_identifier = f"student_{idx+1}"

            name = (
                result.get("name")
                or result.get("student_name")
                or f"Student {student_identifier}"
            )
            student_names[student_identifier] = name

            total = 0.0
            count = 0
            for exercise in EXERCISES:
                value = result.get(exercise)
                if value is None:
                    continue
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    continue
                exercise_totals[exercise] += numeric_value
                exercise_counts[exercise] += 1
                total += numeric_value
                count += 1

            average = total / count if count else 0.0
            student_totals[student_identifier] += average
            student_counts[student_identifier] += 1

        students: List[Dict[str, object]] = []
        for student_identifier, total_average in student_totals.items():
            appearances = student_counts.get(student_identifier, 1)
            mean_average = total_average / appearances if appearances else 0.0
            students.append(
                {
                    "student_id": student_identifier,
                    "name": student_names.get(student_identifier, f"Student {student_identifier}"),
                    "average": round(mean_average, 2),
                }
            )

        students.sort(key=lambda item: item["average"], reverse=True)

        session_average = round(
            sum(student["average"] for student in students) / len(students),
            2,
        ) if students else 0.0

        exercise_averages = {
            exercise: round(exercise_totals[exercise] / exercise_counts[exercise], 2)
            if exercise_counts[exercise]
            else 0.0
            for exercise in EXERCISES
        }

        valid_exercise_averages = {
            exercise: exercise_averages[exercise]
            for exercise in EXERCISES
            if exercise_counts[exercise]
        }

        best_student = students[0] if students else None
        weakest_student = students[-1] if students else None

        best_exercise = None
        weakest_exercise = None
        if valid_exercise_averages:
            best_exercise_name = max(valid_exercise_averages, key=valid_exercise_averages.get)
            weakest_exercise_name = min(valid_exercise_averages, key=valid_exercise_averages.get)
            best_exercise = {
                "exercise_name": best_exercise_name,
                "average": valid_exercise_averages[best_exercise_name],
            }
            weakest_exercise = {
                "exercise_name": weakest_exercise_name,
                "average": valid_exercise_averages[weakest_exercise_name],
            }

        top_3_best = students[:3]
        if len(students) >= 3:
            top_3_worst = students[-3:][::-1]
        else:
            top_3_worst = list(reversed(students))

        return {
            "session_count": 1 if students else 0,
            "student_count": len(students),
            "session_average": session_average,
            "best_student": best_student,
            "weakest_student": weakest_student,
            "top_3_best": top_3_best,
            "top_3_worst": top_3_worst,
            "best_exercise": best_exercise,
            "weakest_exercise": weakest_exercise,
            "exercise_averages": exercise_averages,
            "students": students,
        }

    @staticmethod
    def _empty_response() -> Dict[str, object]:
        return {
            "session_count": 0,
            "student_count": 0,
            "session_average": 0.0,
            "best_student": None,
            "weakest_student": None,
            "top_3_best": [],
            "top_3_worst": [],
            "best_exercise": None,
            "weakest_exercise": None,
            "exercise_averages": {exercise: 0.0 for exercise in EXERCISES},
            "students": [],
        }
