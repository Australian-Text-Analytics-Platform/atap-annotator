import logging

from panel import Row, Column
from panel.widgets import Button, CheckButtonGroup, IntInput
from panel.pane import Str


class Navigator:
    def __init__(self, controller):
        self.controller = controller

        self.document_idx_control = IntInput(value=self.controller.get_min_document_idx(), width=70, step=1,
                                             start=self.controller.get_min_document_idx(),
                                             end=self.controller.get_max_document_idx())
        self.prev_document_button = Button(name="\N{LEFTWARDS ARROW TO BAR} PREV",
                                           button_type="primary", button_style="outline")
        self.next_document_button = Button(name="NEXT \N{RIGHTWARDS ARROW TO BAR}",
                                           button_type="primary", button_style="outline")

        self.prev_document_button.on_click(self.prev_document)
        self.next_document_button.on_click(self.next_document)

        self.reset_button = Button(name="Reset to default", button_type="primary", button_style="outline")
        self.reset_button.on_click(self.reset_to_default)
        self.set_default_button = Button(name="Set as default", button_type="warning", button_style="outline")
        self.set_default_button.on_click(self.set_as_default)
        self.category_selector = CheckButtonGroup(
            options=self.controller.get_all_categories(),
            value=[],
            button_type="primary", button_style="outline"
        )

        self.panel = Column(
            Row(self.prev_document_button,
                Str("Document", align="center"),
                self.document_idx_control,
                self.next_document_button,
                align="center"),
            Row(self.reset_button, self.set_default_button, align="center"),
            Row(self.category_selector, align="center"),
            sizing_mode="stretch_width"
        )

        self.document_idx_control.param.watch(self.set_document_idx, ['value'])
        self.category_selector.param.watch(self.set_categories, ['value'])

    def __panel__(self):
        return self.panel

    def update_display(self):
        self.document_idx_control.value = self.controller.get_curr_document_idx()
        self.document_idx_control.start = self.controller.get_min_document_idx()
        self.document_idx_control.end = self.controller.get_max_document_idx()

        self.category_selector.options = self.controller.get_all_categories()
        self.category_selector.value = self.controller.get_curr_categories()
        self._set_default_buttons()

    def next_document(self, *_):
        self.controller.next_document()

    def prev_document(self, *_):
        self.controller.prev_document()

    def set_document_idx(self, *_):
        document_idx: int = self.document_idx_control.value
        self.controller.set_curr_document_idx(document_idx)
        self.update_display()

    def _set_default_buttons(self):
        classes_are_default = set(self.category_selector.value) == set(self.controller.get_default_categories())
        self.reset_button.disabled = classes_are_default
        self.set_default_button.disabled = classes_are_default
        style: str = "outline" if classes_are_default else "solid"
        self.reset_button.button_style = style
        self.set_default_button.button_style = style

    def reset_to_default(self, *_):
        self.category_selector.value = self.controller.get_default_categories()
        self._set_default_buttons()

    def set_as_default(self, *_):
        self.controller.set_default_categories(self.category_selector.value)
        self._set_default_buttons()

    def set_categories(self, *_):
        self._set_default_buttons()

        self.controller.set_curr_categories(self.category_selector.value)
