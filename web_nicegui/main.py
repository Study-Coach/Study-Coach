from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui import app, ui

from core.ai_service import evaluate_answer, generate_questions, generate_recommendation
from core.analyzer import (
    analyze_study,
    calculate_average_score,
    calculate_review_rate,
    create_dashboard_charts,
    format_created_at,
    summarize_by_subject,
)
from core.models import AnswerEvaluation, Question, StudyInput
from core.storage import add_sample_data, get_all_records, get_recent_records, init_db, save_study_session


CHART_DIR = PROJECT_ROOT / "data" / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)
app.add_static_files("/charts", str(CHART_DIR))
ui.add_head_html(
    """
    <style>
    .study-page-width {
        max-width: 1680px;
    }
    .study-input-layout {
        display: grid;
        grid-template-columns: minmax(620px, 2fr) minmax(360px, 1fr);
        gap: 20px;
        align-items: start;
    }
    .study-metrics-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
    }
    @media (max-width: 1000px) {
        .study-input-layout {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    shared=True,
)

SESSION: dict = {
    "study": None,
    "questions": [],
    "evaluations": [],
    "average_score": 0.0,
    "review_rate": 0.0,
    "recommendation": "",
    "record_id": None,
}


def page_frame(title: str, subtitle: str = ""):
    ui.colors(primary="#2563eb", secondary="#16a34a", accent="#f59e0b")
    ui.query("body").classes("bg-[#f5f7fb] text-[#111827]")

    with ui.header().classes("bg-white text-[#111827] border-b border-[#e5e7eb] shadow-sm"):
        with ui.row().classes("w-full study-page-width mx-auto items-center justify-between px-4 py-2"):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-9 h-9 rounded-lg bg-[#2563eb] text-white flex items-center justify-center"
                ):
                    ui.icon("school").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("AI Study Coach").classes("text-base font-bold leading-tight")
                    ui.label("study planner").classes("text-xs text-[#6b7280] leading-tight")

            with ui.row().classes("items-center gap-2"):
                nav_button("입력", "edit_note", "/")
                nav_button("대시보드", "dashboard", "/dashboard")

    with ui.column().classes("w-full study-page-width mx-auto px-4 py-6 gap-5"):
        with ui.row().classes("w-full items-end justify-between gap-4"):
            with ui.column().classes("gap-1"):
                ui.label(title).classes("text-2xl md:text-3xl font-bold tracking-normal")
                if subtitle:
                    ui.label(subtitle).classes("text-sm text-[#6b7280]")
        return ui.column().classes("w-full gap-5")


def nav_button(label: str, icon: str, target: str) -> None:
    ui.button(label, icon=icon, on_click=lambda: ui.navigate.to(target)).props("flat no-caps").classes(
        "text-[#374151] px-3"
    )


def primary_button(label: str, icon: str, on_click) -> None:
    ui.button(label, icon=icon, on_click=on_click).props("unelevated no-caps").classes(
        "h-11 px-5 rounded-lg bg-[#2563eb] text-white font-semibold"
    )


def secondary_button(label: str, icon: str, on_click) -> None:
    ui.button(label, icon=icon, on_click=on_click).props("outline no-caps").classes(
        "h-11 px-4 rounded-lg text-[#374151]"
    )


def panel(extra: str = ""):
    return ui.card().classes(
        "w-full rounded-xl border border-[#e5e7eb] bg-white shadow-sm p-5 " + extra
    )


def metric_card(label: str, value: str, icon: str, tone: str = "blue") -> None:
    colors = {
        "blue": ("#dbeafe", "#2563eb"),
        "green": ("#dcfce7", "#16a34a"),
        "amber": ("#fef3c7", "#d97706"),
        "slate": ("#e5e7eb", "#374151"),
    }
    bg, fg = colors.get(tone, colors["blue"])
    with panel("p-4"):
        with ui.row().classes("items-center justify-between"):
            with ui.column().classes("gap-1"):
                ui.label(label).classes("text-xs font-medium text-[#6b7280]")
                ui.label(value).classes("text-2xl font-bold")
            with ui.element("div").classes(
                "w-10 h-10 rounded-lg flex items-center justify-center"
            ).style(f"background:{bg}; color:{fg}"):
                ui.icon(icon).classes("text-xl")


def chart_panel(title: str, chart_path: Path, chart_version: int) -> None:
    with panel("p-4"):
        ui.label(title).classes("text-lg font-bold mb-2")
        ui.image(f"/charts/{chart_path.name}?v={chart_version}").props("fit=contain").classes(
            "w-full rounded-lg bg-[#f8fafc]"
        ).style("height: 230px;")


def recent_record_list(records: list[dict]) -> None:
    if not records:
        ui.label("아직 저장된 기록이 없습니다.").classes("text-sm text-[#6b7280]")
        return

    with ui.column().classes("w-full gap-3"):
        for record in records:
            with ui.column().classes(
                "w-full gap-1 rounded-lg border border-[#eef0f4] bg-[#fafbff] px-3 py-3"
            ):
                with ui.row().classes("w-full items-start justify-between gap-2"):
                    with ui.column().classes("gap-0"):
                        ui.label(record["subject"]).classes("font-semibold text-[#111827]")
                        ui.label(format_created_at(record["created_at"])).classes("text-xs text-[#6b7280]")
                    with ui.column().classes("items-end gap-0 shrink-0"):
                        ui.label(f"{record['average_score']:.1f}점").classes("font-bold text-[#2563eb]")
                        ui.label(f"복습률 {record['review_rate']:.1f}%").classes("text-xs text-[#6b7280]")
                ui.label(compact_text(record["study_content"])).classes("text-sm text-[#374151] leading-snug")
                ui.label(f"어려웠던 점: {compact_text(record['difficulty'])}").classes(
                    "text-xs text-[#6b7280] leading-snug"
                )


def dashboard_stats(records: list[dict]) -> tuple[int, float, float, int]:
    if not records:
        return 0, 0.0, 0.0, 0
    total_minutes = sum(int(record["study_minutes"]) for record in records)
    avg_score = sum(float(record["average_score"]) for record in records) / len(records)
    avg_review = sum(float(record["review_rate"]) for record in records) / len(records)
    return total_minutes, avg_score, avg_review, len(records)


def group_records_by_subject(records: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for record in sorted(records, key=lambda item: item["created_at"], reverse=True):
        grouped.setdefault(record["subject"], []).append(record)
    return dict(sorted(grouped.items(), key=lambda item: item[0]))


def compact_text(value: str, fallback: str = "-") -> str:
    text = (value or "").strip()
    return text if text else fallback


def study_record_card(record: dict) -> None:
    with ui.column().classes("w-full gap-2 rounded-lg border border-[#eef0f4] bg-[#fafbff] px-4 py-3"):
        with ui.row().classes("w-full items-start justify-between gap-3"):
            with ui.column().classes("gap-0"):
                ui.label(format_created_at(record["created_at"])).classes("text-xs text-[#6b7280]")
                ui.label(compact_text(record["study_content"])).classes(
                    "font-semibold text-[#111827] leading-snug"
                )
            with ui.column().classes("items-end gap-0 shrink-0"):
                ui.label(f"{record['average_score']:.1f}점").classes("font-bold text-[#2563eb]")
                ui.label(f"복습률 {record['review_rate']:.1f}%").classes("text-xs text-[#6b7280]")

        ui.label(f"어려웠던 점: {compact_text(record['difficulty'])}").classes(
            "text-sm text-[#4b5563] leading-snug"
        )
        ui.label(f"{record['study_minutes']}분 | 집중도 {record['focus_score']}/5").classes(
            "text-xs text-[#6b7280]"
        )


@ui.page("/")
def input_page() -> None:
    init_db()
    recent_records = get_recent_records(limit=3)
    total_minutes, avg_score, avg_review, record_count = dashboard_stats(get_all_records())

    with page_frame("오늘 학습 입력", "공부한 내용을 남기고 바로 복습 문제를 만들어보세요."):
        with ui.element("div").classes("study-input-layout w-full"):
            with ui.column().classes("w-full gap-5"):
                with panel():
                    with ui.row().classes("items-center justify-between mb-2"):
                        with ui.column().classes("gap-0"):
                            ui.label("새 학습 세션").classes("text-lg font-bold")
                            ui.label("과목, 시간, 내용만 입력하면 문제 풀이로 이어집니다.").classes(
                                "text-sm text-[#6b7280]"
                            )

                    subject = ui.input(
                        "과목",
                        placeholder="예: 프로그래밍",
                        value="프로그래밍",
                    ).props("outlined").classes("w-full")

                    with ui.row().classes("w-full gap-4"):
                        study_minutes = ui.number(
                            "공부 시간(분)",
                            value=50,
                            min=1,
                            max=600,
                        ).props("outlined").classes("w-full")
                        focus_score = ui.slider(min=1, max=5, value=4, step=1).props(
                            "label-always color=primary"
                        ).classes("w-full")

                    ui.label("집중도").classes("text-sm font-medium text-[#374151] -mb-2")
                    study_content = ui.textarea(
                        "오늘 공부한 내용",
                        placeholder="예: 파이썬 리스트, 반복문, 조건문",
                    ).props("outlined autogrow").classes("w-full")
                    difficulty = ui.textarea(
                        "어려웠던 점",
                        placeholder="예: while문 조건이 헷갈림",
                    ).props("outlined autogrow").classes("w-full")

                    def create_questions() -> None:
                        content = (study_content.value or "").strip()
                        subject_value = (subject.value or "").strip()
                        if not subject_value:
                            ui.notify("과목을 입력해주세요.", type="warning")
                            return
                        if not content:
                            ui.notify("오늘 공부한 내용을 입력해주세요.", type="warning")
                            return

                        study = StudyInput(
                            subject=subject_value,
                            study_minutes=int(study_minutes.value or 0),
                            focus_score=int(focus_score.value or 3),
                            study_content=content,
                            difficulty=(difficulty.value or "").strip(),
                        )
                        SESSION["study"] = study
                        SESSION["questions"] = generate_questions(study.study_content, study.difficulty)
                        ui.navigate.to("/quiz")

                    with ui.row().classes("w-full justify-end mt-2"):
                        primary_button("AI 문제 5개 생성", "auto_awesome", create_questions)

            with ui.column().classes("w-full gap-5"):
                with ui.element("div").classes("study-metrics-grid w-full"):
                    metric_card("기록", f"{record_count}개", "folder_open", "slate")
                    metric_card("복습률", f"{avg_review:.0f}%", "task_alt", "green")
                    metric_card("공부 시간", f"{total_minutes}분", "timer", "blue")
                    metric_card("평균 점수", f"{avg_score:.0f}점", "grade", "amber")

                with panel():
                    with ui.row().classes("items-center justify-between mb-2"):
                        ui.label("최근 학습 기록").classes("text-lg font-bold")
                        ui.button("전체", icon="chevron_right", on_click=lambda: ui.navigate.to("/dashboard")).props(
                            "flat dense no-caps"
                        ).classes("text-[#2563eb]")
                    recent_record_list(recent_records)


@ui.page("/quiz")
def quiz_page() -> None:
    questions: list[Question] = SESSION.get("questions") or []
    if not questions:
        ui.navigate.to("/")
        return

    with page_frame("문제 풀이", "생성된 문제에 답변하면 점수와 피드백이 저장됩니다."):
        answer_inputs = []
        with ui.column().classes("w-full gap-4"):
            for index, question in enumerate(questions, start=1):
                with panel():
                    with ui.row().classes("items-start gap-3"):
                        ui.badge(str(index)).classes("bg-[#dbeafe] text-[#2563eb] rounded-md px-2 py-1")
                        with ui.column().classes("w-full gap-3"):
                            ui.label(f"[{question.question_type}] {question.text}").classes(
                                "text-base font-semibold leading-relaxed"
                            )
                            answer_inputs.append(
                                ui.textarea("답변", placeholder="여기에 답변을 입력하세요.")
                                .props("outlined autogrow")
                                .classes("w-full")
                            )

            def submit_answers() -> None:
                study: StudyInput = SESSION["study"]
                evaluations: list[AnswerEvaluation] = []
                for question, answer in zip(questions, answer_inputs, strict=False):
                    evaluations.append(evaluate_answer(question.text, (answer.value or "").strip()))

                answered_count = sum(1 for item in evaluations if item.answer.strip())
                average_score = calculate_average_score(evaluations)
                review_rate = calculate_review_rate(len(questions), answered_count)
                python_analysis = analyze_study(
                    review_rate,
                    study.focus_score,
                    study.study_minutes,
                    average_score,
                )
                recommendation = generate_recommendation(
                    study,
                    review_rate,
                    average_score,
                    python_analysis,
                )
                record_id = save_study_session(
                    study,
                    questions,
                    evaluations,
                    average_score,
                    review_rate,
                    recommendation,
                )

                SESSION["evaluations"] = evaluations
                SESSION["average_score"] = average_score
                SESSION["review_rate"] = review_rate
                SESSION["recommendation"] = recommendation
                SESSION["record_id"] = record_id
                ui.navigate.to("/result")

            with ui.row().classes("w-full justify-between"):
                secondary_button("입력으로 돌아가기", "arrow_back", lambda: ui.navigate.to("/"))
                primary_button("답변 제출", "send", submit_answers)


@ui.page("/result")
def result_page() -> None:
    evaluations: list[AnswerEvaluation] = SESSION.get("evaluations") or []
    if not evaluations:
        ui.navigate.to("/")
        return

    with page_frame("학습 결과", "답변 피드백과 내일 학습 계획을 확인하세요."):
        with ui.row().classes("w-full gap-4"):
            metric_card("평균 점수", f"{SESSION['average_score']:.1f}점", "grade", "amber")
            metric_card("복습률", f"{SESSION['review_rate']:.1f}%", "task_alt", "green")

        with ui.row().classes("w-full gap-5 items-start"):
            with ui.column().classes("w-full lg:w-2/3 gap-4"):
                with panel():
                    ui.label("문제별 피드백").classes("text-lg font-bold mb-3")
                    with ui.column().classes("w-full gap-3"):
                        for index, item in enumerate(evaluations, start=1):
                            with ui.row().classes(
                                "w-full items-start gap-3 rounded-lg bg-[#fafbff] border border-[#eef0f4] px-3 py-3"
                            ):
                                ui.badge(f"{item.score}점").classes("bg-[#dbeafe] text-[#2563eb] rounded-md")
                                ui.label(f"{index}. {item.feedback}").classes("text-sm leading-relaxed")

            with ui.column().classes("w-full lg:w-1/3 gap-4"):
                with panel():
                    ui.label("내일 학습 추천").classes("text-lg font-bold mb-3")
                    ui.markdown(SESSION["recommendation"].replace("\n", "\n\n")).classes(
                        "text-sm leading-relaxed"
                    )

                with ui.row().classes("w-full gap-2"):
                    secondary_button("새 기록 작성", "add", lambda: ui.navigate.to("/"))
                    primary_button("대시보드", "dashboard", lambda: ui.navigate.to("/dashboard"))


@ui.page("/dashboard")
def dashboard_page() -> None:
    init_db()
    records = get_all_records()
    charts = create_dashboard_charts(records, CHART_DIR)
    subject_totals = summarize_by_subject(records)
    total_minutes, avg_score, avg_review, record_count = dashboard_stats(records)
    chart_version = int(time.time())

    with page_frame("대시보드", "학습 기록과 복습 흐름을 한 화면에서 확인하세요."):
        with ui.row().classes("w-full justify-between items-center gap-3"):
            with ui.row().classes("gap-2"):
                secondary_button("새로고침", "refresh", lambda: ui.navigate.to("/dashboard"))

                def add_sample() -> None:
                    add_sample_data()
                    ui.navigate.to("/dashboard")

                secondary_button("샘플 데이터 추가", "dataset", add_sample)

        with ui.element("div").classes("grid w-full grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4"):
            metric_card("총 기록", f"{record_count}개", "folder_open", "slate")
            metric_card("총 공부 시간", f"{total_minutes}분", "timer", "blue")
            metric_card("평균 점수", f"{avg_score:.1f}점", "grade", "amber")
            metric_card("평균 복습률", f"{avg_review:.1f}%", "task_alt", "green")

        with ui.element("div").classes("grid w-full grid-cols-1 lg:grid-cols-2 gap-4"):
            chart_panel("과목별 공부 시간", charts["subject_minutes"], chart_version)
            chart_panel("날짜별 평균 복습률", charts["daily_review_rate"], chart_version)

        with ui.element("div").classes("grid w-full grid-cols-1 lg:grid-cols-3 gap-4"):
            with panel("lg:col-span-1"):
                ui.label("과목 요약").classes("text-lg font-bold mb-3")
                if subject_totals:
                    with ui.column().classes("w-full gap-2"):
                        for subject, minutes in sorted(subject_totals.items(), key=lambda item: item[1], reverse=True):
                            with ui.row().classes("w-full items-center justify-between"):
                                ui.label(subject).classes("font-medium")
                                ui.badge(f"{minutes}분").classes("bg-[#dbeafe] text-[#2563eb]")
                else:
                    ui.label("저장된 학습 기록이 없습니다.").classes("text-sm text-[#6b7280]")

            with panel("lg:col-span-2"):
                ui.label("학습 기록").classes("text-lg font-bold mb-3")
                grouped_records = group_records_by_subject(records)
                if not grouped_records:
                    ui.label("저장된 학습 기록이 없습니다.").classes("text-sm text-[#6b7280]")
                else:
                    with ui.column().classes("w-full gap-4"):
                        for subject, subject_records in grouped_records.items():
                            with ui.column().classes("w-full gap-2"):
                                with ui.row().classes("w-full items-center justify-between"):
                                    ui.label(subject).classes("font-bold text-[#111827]")
                                    ui.badge(f"{len(subject_records)}개").classes("bg-[#dbeafe] text-[#2563eb]")
                                for record in subject_records:
                                    study_record_card(record)


if __name__ in {"__main__", "__mp_main__"}:
    init_db()
    ui.run(title="AI Study Coach", reload=False)
