from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput

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


FONT_PATH = Path("C:/Windows/Fonts/malgun.ttf")
BOLD_FONT_PATH = Path("C:/Windows/Fonts/malgunbd.ttf")
if FONT_PATH.exists():
    LabelBase.register(
        name="Korean",
        fn_regular=str(FONT_PATH),
        fn_bold=str(BOLD_FONT_PATH if BOLD_FONT_PATH.exists() else FONT_PATH),
    )
    DEFAULT_FONT = "Korean"
else:
    DEFAULT_FONT = "Roboto"


BG = (0.95, 0.96, 0.98, 1)
WHITE = (1, 1, 1, 1)
BORDER = (0.82, 0.86, 0.92, 1)
FIELD_BG = (0.96, 0.98, 1, 1)
TEXT = (0.04, 0.06, 0.12, 1)
MUTED = (0.32, 0.36, 0.44, 1)
BLUE = (0.15, 0.39, 0.92, 1)
GREEN = (0.09, 0.64, 0.29, 1)
AMBER = (0.86, 0.47, 0.04, 1)
SLATE = (0.22, 0.26, 0.32, 1)

Window.clearcolor = BG
Window.minimum_width = 1000
Window.minimum_height = 720


class PaintedBox(BoxLayout):
    def __init__(self, bg_color=BG, border_color=None, radius: int = 0, border_width: float = 1.2, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.radius = radius
        self.border_width = border_width
        with self.canvas.before:
            Color(*self.bg_color)
            if radius:
                self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(radius)])
            else:
                self._bg = Rectangle(pos=self.pos, size=self.size)
        self._border = None
        if border_color:
            with self.canvas.after:
                Color(*border_color)
                if radius:
                    self._border = Line(
                        rounded_rectangle=(self.x, self.y, self.width, self.height, dp(radius)),
                        width=self.border_width,
                    )
                else:
                    self._border = Line(rectangle=(self.x, self.y, self.width, self.height), width=self.border_width)
        self.bind(pos=self._update_shape, size=self._update_shape)

    def _update_shape(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        if self._border:
            if self.radius:
                self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(self.radius))
            else:
                self._border.rectangle = (self.x, self.y, self.width, self.height)


class Card(PaintedBox):
    def __init__(self, **kwargs):
        super().__init__(bg_color=WHITE, border_color=BORDER, radius=14, **kwargs)
        self.padding = kwargs.get("padding", [dp(20), dp(18)])
        self.spacing = kwargs.get("spacing", dp(12))
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))


class AppButton(Button):
    def __init__(self, text: str, variant: str = "primary", **kwargs):
        if variant == "secondary":
            self._bg_color = WHITE
            self._border_color = BORDER
            text_color = SLATE
        else:
            self._bg_color = BLUE
            self._border_color = BLUE
            text_color = WHITE

        super().__init__(
            text=text,
            font_name=DEFAULT_FONT,
            font_size=dp(15),
            bold=True,
            color=text_color,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            size_hint_y=None,
            height=dp(48),
            **kwargs,
        )
        with self.canvas.before:
            Color(*self._bg_color)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        with self.canvas.after:
            Color(*self._border_color)
            self._border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)), width=1.3)
        self.bind(pos=self._update_shape, size=self._update_shape)

    def _update_shape(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(8))


def bind_click(button: Button, callback):
    button.bind(on_press=callback)
    return button


def label(
    text: str,
    size: int = 14,
    bold: bool = False,
    color=TEXT,
    height: int = 30,
    halign: str = "left",
    valign: str = "middle",
) -> Label:
    widget = Label(
        text=text,
        font_name=DEFAULT_FONT,
        font_size=dp(size),
        bold=bold,
        color=color,
        halign=halign,
        valign=valign,
        size_hint_y=None,
        height=dp(height),
    )
    widget.bind(width=lambda instance, value: setattr(instance, "text_size", (value, None)))
    return widget


def input_box(hint: str, multiline: bool = False, height: int = 44) -> TextInput:
    return TextInput(
        hint_text=hint,
        font_name=DEFAULT_FONT,
        font_size=dp(15),
        multiline=multiline,
        size_hint_y=None,
        height=dp(height),
        padding=[dp(14), dp(11), dp(14), dp(11)],
        background_normal="",
        background_active="",
        background_color=FIELD_BG,
        foreground_color=TEXT,
        hint_text_color=(0.58, 0.62, 0.69, 1),
        cursor_color=BLUE,
        write_tab=False,
    )


def field(title: str, widget, height: int | None = None) -> BoxLayout:
    box_height = height if height is not None else int(widget.height + dp(34))
    box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None, height=box_height)
    box.add_widget(label(title, 13, True, SLATE, 24))
    box.add_widget(widget)
    return box


def top_bar(screen: Screen) -> PaintedBox:
    bar = PaintedBox(
        orientation="vertical",
        bg_color=WHITE,
        border_color=BORDER,
        size_hint_y=None,
        height=dp(72),
    )

    anchor = AnchorLayout(anchor_x="center", anchor_y="center", padding=[dp(24), dp(10)])
    inner = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_x=None, width=dp(1120))
    bind_center_width(inner)

    brand = BoxLayout(orientation="horizontal", spacing=dp(10))
    icon = PaintedBox(
        bg_color=BLUE,
        radius=9,
        size_hint=(None, None),
        size=(dp(44), dp(44)),
        padding=[0, 0],
    )
    icon.add_widget(label("AI", 14, True, WHITE, 44, "center"))
    brand.add_widget(icon)
    title_box = BoxLayout(orientation="vertical", spacing=0)
    title_box.add_widget(label("AI Study Coach", 16, True, TEXT, 25))
    title_box.add_widget(label("study planner", 12, False, MUTED, 19))
    brand.add_widget(title_box)
    inner.add_widget(brand)

    nav = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint=(None, None), width=dp(220), height=dp(48))
    nav.add_widget(bind_click(AppButton("입력", "secondary"), lambda _btn: setattr(screen.manager, "current", "input")))
    nav.add_widget(
        bind_click(AppButton("대시보드", "secondary"), lambda _btn: show_dashboard(screen.manager))
    )
    inner.add_widget(nav)
    anchor.add_widget(inner)
    bar.add_widget(anchor)
    return bar


def bind_center_width(widget) -> None:
    def update_width(*_args) -> None:
        widget.width = min(Window.width - dp(44), dp(1120))

    update_width()
    Window.bind(width=update_width)


def page_shell(screen: Screen, title: str, subtitle: str) -> tuple[BoxLayout, BoxLayout]:
    root = PaintedBox(orientation="vertical", bg_color=BG)
    root.add_widget(top_bar(screen))

    scroll = ScrollView(bar_width=dp(7))
    viewport = AnchorLayout(anchor_x="center", anchor_y="top", size_hint=(1, None))
    content = BoxLayout(
        orientation="vertical",
        spacing=dp(20),
        padding=[0, dp(28), 0, dp(32)],
        size_hint=(None, None),
    )
    content.bind(minimum_height=content.setter("height"))
    bind_center_width(content)

    heading = BoxLayout(orientation="vertical", spacing=dp(3), size_hint_y=None, height=dp(76))
    heading.add_widget(label(title, 30, True, TEXT, 44))
    heading.add_widget(label(subtitle, 15, False, MUTED, 28))
    content.add_widget(heading)

    def sync_viewport_height(*_args) -> None:
        viewport.height = max(content.height, scroll.height)

    content.bind(height=sync_viewport_height)
    scroll.bind(height=sync_viewport_height)
    sync_viewport_height()

    viewport.add_widget(content)
    scroll.add_widget(viewport)
    root.add_widget(scroll)
    return root, content


def metric_card(title: str, value: str, color=BLUE) -> Card:
    card = Card(orientation="vertical", padding=[dp(16), dp(12)], spacing=dp(2), size_hint_y=None)
    card.height = dp(90)
    card.add_widget(label(title, 13, True, MUTED, 26))
    card.add_widget(label(value, 24, True, color, 42))
    return card


def recent_item(record: dict) -> Card:
    card = Card(orientation="vertical", padding=[dp(16), dp(12)], spacing=dp(2), size_hint_y=None)
    card.height = dp(176)
    card.add_widget(label(record["subject"], 16, True, TEXT, 30))
    card.add_widget(label(format_created_at(record["created_at"]), 12, False, MUTED, 24))
    card.add_widget(label(compact_text(record["study_content"]), 14, True, TEXT, 38))
    card.add_widget(label(f"어려웠던 점: {compact_text(record['difficulty'])}", 13, False, MUTED, 34))
    card.add_widget(
        label(
            f"평균 {record['average_score']:.1f}점  |  복습률 {record['review_rate']:.1f}%  |  {record['study_minutes']}분",
            13,
            True,
            BLUE,
            30,
        )
    )
    return card


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


def show_dashboard(manager: ScreenManager) -> None:
    dashboard = manager.get_screen("dashboard")
    dashboard.load_dashboard()
    manager.current = "dashboard"


class StudyInputScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root, content = page_shell(self, "오늘 학습 입력", "공부한 내용을 남기고 바로 복습 문제를 만들어보세요.")

        main = BoxLayout(orientation="horizontal", spacing=dp(18), size_hint_y=None)
        main.bind(minimum_height=main.setter("height"))

        form_column = BoxLayout(orientation="vertical", spacing=0, size_hint_x=0.66, size_hint_y=1)
        form_card = Card(orientation="vertical", padding=[dp(22), dp(20)], spacing=dp(14), size_hint_x=1)
        form_card.add_widget(label("새 학습 세션", 22, True, TEXT, 34))
        form_card.add_widget(label("과목, 시간, 내용만 입력하면 문제 풀이로 이어집니다.", 15, False, MUTED, 28))

        self.subject = input_box("예: 프로그래밍")
        form_card.add_widget(field("과목", self.subject))

        top_fields = BoxLayout(orientation="horizontal", spacing=dp(14), size_hint_y=None, height=dp(84))
        self.study_minutes = input_box("예: 50")
        self.study_minutes.input_filter = "int"
        top_fields.add_widget(field("공부 시간(분)", self.study_minutes, dp(84)))

        focus_wrap = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(44))
        self.focus_score = Slider(min=1, max=5, value=4, step=1, cursor_size=(dp(18), dp(18)))
        self.focus_score.value_track = True
        self.focus_score.value_track_color = BLUE
        self.focus_value = label("4", 15, True, TEXT, 44, "center")
        self.focus_value.size_hint_x = None
        self.focus_value.width = dp(42)
        self.focus_score.bind(value=lambda _slider, value: setattr(self.focus_value, "text", str(int(value))))
        focus_wrap.add_widget(self.focus_score)
        focus_wrap.add_widget(self.focus_value)
        top_fields.add_widget(field("집중도", focus_wrap, dp(84)))
        form_card.add_widget(top_fields)

        self.study_content = input_box("예: 파이썬 리스트, 반복문, 조건문", True, 126)
        form_card.add_widget(field("오늘 공부한 내용", self.study_content, dp(160)))

        self.difficulty = input_box("예: while문 조건이 헷갈림", True, 104)
        form_card.add_widget(field("어려웠던 점", self.difficulty, dp(138)))

        action_row = BoxLayout(orientation="horizontal", spacing=dp(14), size_hint_y=None, height=dp(48))
        action_row.add_widget(bind_click(AppButton("최근 기록", "secondary"), self.open_dashboard))
        action_row.add_widget(bind_click(AppButton("AI 문제 5개 생성", "primary"), self.generate_quiz))
        form_card.add_widget(action_row)

        self.message = label("", 13, False, AMBER, 24)
        form_card.add_widget(self.message)
        form_column.add_widget(form_card)
        form_column.add_widget(BoxLayout(size_hint_y=1))
        main.add_widget(form_column)

        side = BoxLayout(orientation="vertical", spacing=dp(16), size_hint_x=0.34, size_hint_y=None)
        side.bind(minimum_height=side.setter("height"))
        metrics = GridLayout(cols=2, spacing=dp(12), size_hint_y=None, height=dp(192))
        self.metric_records = metric_card("기록", "0개", SLATE)
        self.metric_review = metric_card("복습률", "0%", GREEN)
        self.metric_minutes = metric_card("공부 시간", "0분", BLUE)
        self.metric_score = metric_card("평균 점수", "0점", AMBER)
        metrics.add_widget(self.metric_records)
        metrics.add_widget(self.metric_review)
        metrics.add_widget(self.metric_minutes)
        metrics.add_widget(self.metric_score)
        side.add_widget(metrics)

        self.recent_card = Card(orientation="vertical", padding=[dp(22), dp(20)], spacing=dp(12), size_hint_y=None)
        self.recent_card.add_widget(label("최근 학습 기록", 22, True, TEXT, 34))
        self.recent_card.add_widget(label("최근 3개의 학습 흐름을 확인하세요.", 15, False, MUTED, 28))
        self.recent_box = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None)
        self.recent_box.bind(minimum_height=self.recent_box.setter("height"))
        self.recent_card.add_widget(self.recent_box)
        side.add_widget(self.recent_card)
        main.add_widget(side)

        content.add_widget(main)
        self.add_widget(root)

    def on_pre_enter(self, *_args) -> None:
        self.refresh_summary()

    def refresh_summary(self) -> None:
        records = get_all_records()
        total_minutes, avg_score, avg_review, record_count = dashboard_stats(records)
        self.metric_records.children[0].text = f"{record_count}개"
        self.metric_review.children[0].text = f"{avg_review:.0f}%"
        self.metric_minutes.children[0].text = f"{total_minutes}분"
        self.metric_score.children[0].text = f"{avg_score:.0f}점"

        self.recent_box.clear_widgets()
        recent = get_recent_records(limit=3)
        if not recent:
            self.recent_card.height = dp(168)
            self.recent_box.add_widget(label("아직 저장된 기록이 없습니다.", 13, False, MUTED, 44))
            return
        self.recent_card.height = dp(128 + len(recent) * 188)
        for record in recent:
            self.recent_box.add_widget(recent_item(record))

    def generate_quiz(self, _button) -> None:
        try:
            study_minutes = int(self.study_minutes.text.strip())
        except ValueError:
            self.message.text = "공부 시간은 숫자로 입력해주세요."
            return

        study_content = self.study_content.text.strip()
        difficulty = self.difficulty.text.strip()
        subject = self.subject.text.strip()
        if not subject:
            self.message.text = "과목을 입력해주세요."
            return
        if not study_content:
            self.message.text = "오늘 공부한 내용을 입력해주세요."
            return

        app = App.get_running_app()
        app.current_study = StudyInput(
            subject=subject,
            study_minutes=study_minutes,
            focus_score=int(self.focus_score.value),
            study_content=study_content,
            difficulty=difficulty,
        )
        self.message.text = "문제를 생성하는 중입니다..."
        app.current_questions = generate_questions(study_content, difficulty)
        quiz_screen = self.manager.get_screen("quiz")
        quiz_screen.load_questions(app.current_questions)
        self.manager.current = "quiz"

    def open_dashboard(self, _button) -> None:
        show_dashboard(self.manager)


class QuizScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.answer_inputs: list[TextInput] = []
        root, content = page_shell(self, "문제 풀이", "생성된 문제에 답변하면 점수와 피드백이 저장됩니다.")

        self.question_box = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None)
        self.question_box.bind(minimum_height=self.question_box.setter("height"))
        content.add_widget(self.question_box)

        actions = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(48))
        actions.add_widget(bind_click(AppButton("입력으로 돌아가기", "secondary"), self.back_to_input))
        actions.add_widget(bind_click(AppButton("답변 제출", "primary"), self.submit_answers))
        content.add_widget(actions)
        self.add_widget(root)

    def load_questions(self, questions: list[Question]) -> None:
        self.question_box.clear_widgets()
        self.answer_inputs = []
        for index, question in enumerate(questions, start=1):
            card = Card(orientation="vertical", padding=[dp(22), dp(18)], spacing=dp(10))
            card.add_widget(label(f"{index}. [{question.question_type}]", 14, True, BLUE, 26))
            card.add_widget(label(question.text, 16, True, TEXT, 52))
            answer = input_box("여기에 답변을 입력하세요.", True, 102)
            self.answer_inputs.append(answer)
            card.add_widget(answer)
            self.question_box.add_widget(card)

    def submit_answers(self, _button) -> None:
        app = App.get_running_app()
        evaluations: list[AnswerEvaluation] = []
        for question, answer_input in zip(app.current_questions, self.answer_inputs, strict=False):
            evaluations.append(evaluate_answer(question.text, answer_input.text.strip()))

        answered_count = sum(1 for item in evaluations if item.answer.strip())
        average_score = calculate_average_score(evaluations)
        review_rate = calculate_review_rate(len(app.current_questions), answered_count)
        python_analysis = analyze_study(
            review_rate,
            app.current_study.focus_score,
            app.current_study.study_minutes,
            average_score,
        )
        recommendation = generate_recommendation(
            app.current_study,
            review_rate,
            average_score,
            python_analysis,
        )

        record_id = save_study_session(
            app.current_study,
            app.current_questions,
            evaluations,
            average_score,
            review_rate,
            recommendation,
        )

        app.current_evaluations = evaluations
        app.current_average_score = average_score
        app.current_review_rate = review_rate
        app.current_recommendation = recommendation
        app.current_record_id = record_id

        result_screen = self.manager.get_screen("result")
        result_screen.show_result(evaluations, average_score, review_rate, recommendation)
        self.manager.current = "result"

    def back_to_input(self, _button) -> None:
        self.manager.current = "input"


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root, content = page_shell(self, "학습 결과", "답변 피드백과 내일 학습 계획을 확인하세요.")

        self.metric_row = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(92))
        content.add_widget(self.metric_row)

        result_grid = BoxLayout(orientation="horizontal", spacing=dp(18), size_hint_y=None)
        result_grid.bind(minimum_height=result_grid.setter("height"))
        self.feedback_box = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_x=0.66, size_hint_y=None)
        self.feedback_box.bind(minimum_height=self.feedback_box.setter("height"))
        self.recommendation_box = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_x=0.34, size_hint_y=None)
        self.recommendation_box.bind(minimum_height=self.recommendation_box.setter("height"))
        result_grid.add_widget(self.feedback_box)
        result_grid.add_widget(self.recommendation_box)
        content.add_widget(result_grid)

        actions = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(48))
        actions.add_widget(bind_click(AppButton("새 기록 작성", "secondary"), self.new_session))
        actions.add_widget(bind_click(AppButton("대시보드", "primary"), self.open_dashboard))
        content.add_widget(actions)
        self.add_widget(root)

    def show_result(
        self,
        evaluations: list[AnswerEvaluation],
        average_score: float,
        review_rate: float,
        recommendation: str,
    ) -> None:
        self.metric_row.clear_widgets()
        self.metric_row.add_widget(metric_card("평균 점수", f"{average_score:.1f}점", AMBER))
        self.metric_row.add_widget(metric_card("복습률", f"{review_rate:.1f}%", GREEN))

        self.feedback_box.clear_widgets()
        feedback_card = Card(orientation="vertical", padding=[dp(22), dp(20)], spacing=dp(12))
        feedback_card.add_widget(label("문제별 피드백", 22, True, TEXT, 34))
        for index, item in enumerate(evaluations, start=1):
            item_card = PaintedBox(
                orientation="horizontal",
                bg_color=FIELD_BG,
                border_color=BORDER,
                radius=10,
                padding=[dp(14), dp(10)],
                spacing=dp(8),
                size_hint_y=None,
                height=dp(66),
            )
            score = label(f"{item.score}점", 14, True, BLUE, 44, "center")
            score.size_hint_x = None
            score.width = dp(70)
            item_card.add_widget(score)
            item_card.add_widget(label(f"{index}. {item.feedback}", 14, False, TEXT, 44))
            feedback_card.add_widget(item_card)
        self.feedback_box.add_widget(feedback_card)

        self.recommendation_box.clear_widgets()
        rec_card = Card(orientation="vertical", padding=[dp(22), dp(20)], spacing=dp(12))
        rec_card.add_widget(label("내일 학습 추천", 22, True, TEXT, 34))
        rec_card.add_widget(label(recommendation, 14, False, TEXT, 240))
        self.recommendation_box.add_widget(rec_card)

    def new_session(self, _button) -> None:
        self.manager.current = "input"

    def open_dashboard(self, _button) -> None:
        show_dashboard(self.manager)


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root, content = page_shell(self, "대시보드", "학습 기록과 복습 흐름을 한 화면에서 확인하세요.")

        controls = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(48))
        controls.add_widget(bind_click(AppButton("새로고침", "secondary"), self.refresh))
        controls.add_widget(bind_click(AppButton("샘플 데이터 추가", "secondary"), self.add_sample))
        content.add_widget(controls)

        self.metrics = GridLayout(cols=4, spacing=dp(12), size_hint_y=None, height=dp(92))
        content.add_widget(self.metrics)

        chart_row = BoxLayout(orientation="horizontal", spacing=dp(18), size_hint_y=None, height=dp(260))
        self.subject_chart_card = PaintedBox(
            orientation="vertical",
            bg_color=WHITE,
            border_color=BORDER,
            radius=14,
            padding=[dp(22), dp(18)],
            spacing=dp(10),
            size_hint_x=0.5,
        )
        self.subject_chart_card.add_widget(label("과목별 공부 시간", 22, True, TEXT, 34))
        self.subject_chart = Image(allow_stretch=True, keep_ratio=True)
        self.subject_chart_card.add_widget(self.subject_chart)
        chart_row.add_widget(self.subject_chart_card)

        self.review_chart_card = PaintedBox(
            orientation="vertical",
            bg_color=WHITE,
            border_color=BORDER,
            radius=14,
            padding=[dp(22), dp(18)],
            spacing=dp(10),
            size_hint_x=0.5,
        )
        self.review_chart_card.add_widget(label("날짜별 평균 복습률", 22, True, TEXT, 34))
        self.review_chart = Image(allow_stretch=True, keep_ratio=True)
        self.review_chart_card.add_widget(self.review_chart)
        chart_row.add_widget(self.review_chart_card)
        content.add_widget(chart_row)

        bottom = BoxLayout(orientation="horizontal", spacing=dp(18), size_hint_y=None)
        bottom.bind(minimum_height=bottom.setter("height"))
        subject_column = BoxLayout(orientation="vertical", spacing=0, size_hint_x=0.34, size_hint_y=1)
        self.subject_summary = Card(orientation="vertical", padding=[dp(22), dp(20)], spacing=dp(12), size_hint_x=1)
        subject_column.add_widget(self.subject_summary)
        subject_column.add_widget(BoxLayout(size_hint_y=1))
        self.records_card = Card(orientation="vertical", padding=[dp(22), dp(20)], spacing=dp(12), size_hint_x=0.66)
        bottom.add_widget(subject_column)
        bottom.add_widget(self.records_card)
        content.add_widget(bottom)

        self.add_widget(root)

    def on_pre_enter(self, *_args) -> None:
        self.load_dashboard()

    def refresh(self, _button) -> None:
        self.load_dashboard()

    def add_sample(self, _button) -> None:
        add_sample_data()
        self.load_dashboard()

    def load_dashboard(self) -> None:
        records = get_all_records()
        charts = create_dashboard_charts(records, PROJECT_ROOT / "data" / "charts")
        totals = summarize_by_subject(records)
        total_minutes, avg_score, avg_review, record_count = dashboard_stats(records)

        self.metrics.clear_widgets()
        self.metrics.add_widget(metric_card("총 기록", f"{record_count}개", SLATE))
        self.metrics.add_widget(metric_card("총 공부 시간", f"{total_minutes}분", BLUE))
        self.metrics.add_widget(metric_card("평균 점수", f"{avg_score:.1f}점", AMBER))
        self.metrics.add_widget(metric_card("평균 복습률", f"{avg_review:.1f}%", GREEN))

        self.subject_chart.source = str(charts["subject_minutes"])
        self.subject_chart.reload()
        self.review_chart.source = str(charts["daily_review_rate"])
        self.review_chart.reload()

        self.subject_summary.clear_widgets()
        self.subject_summary.add_widget(label("과목 요약", 22, True, TEXT, 34))
        if totals:
            self.subject_summary.height = dp(80 + len(totals) * 64)
            for subject, minutes in sorted(totals.items(), key=lambda item: item[1], reverse=True):
                row = PaintedBox(
                    orientation="horizontal",
                    bg_color=FIELD_BG,
                    border_color=BORDER,
                    radius=9,
                    padding=[dp(14), dp(8)],
                    size_hint_y=None,
                    height=dp(52),
                )
                row.add_widget(label(subject, 15, True, TEXT, 34))
                value = label(f"{minutes}분", 15, True, BLUE, 34, "right")
                value.size_hint_x = None
                value.width = dp(70)
                row.add_widget(value)
                self.subject_summary.add_widget(row)
        else:
            self.subject_summary.height = dp(132)
            self.subject_summary.add_widget(label("저장된 학습 기록이 없습니다.", 14, False, MUTED, 42))

        self.records_card.clear_widgets()
        self.records_card.add_widget(label("학습 기록", 22, True, TEXT, 34))
        grouped_records = group_records_by_subject(records)
        if not grouped_records:
            self.records_card.height = dp(132)
            self.records_card.add_widget(label("저장된 학습 기록이 없습니다.", 14, False, MUTED, 42))
        else:
            total_records = sum(len(items) for items in grouped_records.values())
            self.records_card.height = dp(92 + len(grouped_records) * 54 + total_records * 188)
            for subject, subject_records in grouped_records.items():
                subject_row = PaintedBox(
                    orientation="horizontal",
                    bg_color=(0.93, 0.96, 1, 1),
                    border_color=BORDER,
                    radius=9,
                    padding=[dp(14), dp(8)],
                    size_hint_y=None,
                    height=dp(44),
                )
                subject_row.add_widget(label(subject, 15, True, TEXT, 28))
                count = label(f"{len(subject_records)}개", 13, True, BLUE, 28, "right")
                count.size_hint_x = None
                count.width = dp(64)
                subject_row.add_widget(count)
                self.records_card.add_widget(subject_row)
                for record in subject_records:
                    self.records_card.add_widget(recent_item(record))


class StudyCoachApp(App):
    current_study: StudyInput | None = None
    current_questions: list[Question] = []
    current_evaluations: list[AnswerEvaluation] = []
    current_average_score: float = 0.0
    current_review_rate: float = 0.0
    current_recommendation: str = ""
    current_record_id: int | None = None

    def build(self):
        init_db()
        self.title = "AI Study Coach"
        manager = ScreenManager()
        manager.add_widget(StudyInputScreen(name="input"))
        manager.add_widget(QuizScreen(name="quiz"))
        manager.add_widget(ResultScreen(name="result"))
        manager.add_widget(DashboardScreen(name="dashboard"))
        return manager


if __name__ == "__main__":
    StudyCoachApp().run()
