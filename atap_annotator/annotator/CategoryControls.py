from panel import Row, Column
from panel.widgets import Button, TextInput


class CategoryControls:
    def __init__(self, controller):
        self.controller = controller
        self.show_controls: bool = False

        self.category_input = TextInput(name='Category', width=150)
        self.add_category_button = Button(
            name="Add category",
            button_type="primary", button_style="solid",
            align='end', width=120
        )
        self.show_category_controls_button = Button(name='Show categories',
                                                    button_type="primary", button_style="outline", align='start')
        self.category_controls = Row(self.category_input, self.add_category_button)
        self.remove_category_buttons = Row()

        self.panel = Column(
            self.show_category_controls_button,
            self.category_controls,
            self.remove_category_buttons
        )

        self.show_category_controls_button.on_click(self._toggle_category_controls)
        self.add_category_button.on_click(self._add_category)

        self.update_display()

    def __panel__(self):
        return self.panel

    def update_display(self, *_):
        remove_buttons = []
        curr_categories: list[str] = self.controller.get_all_categories()
        for category in curr_categories:
            label = f'{category} \U00002A09'
            remove_button = Button(name=label, button_style="solid")
            remove_button.on_click(lambda *_, term=category: self._remove_category(term))
            remove_buttons.append(remove_button)
        self.remove_category_buttons.objects = remove_buttons

        self.category_controls.visible = self.show_controls
        self.remove_category_buttons.visible = self.show_controls
        if self.show_controls:
            self.show_category_controls_button.name = 'Hide categories'
            self.show_category_controls_button.button_style = 'solid'
        else:
            self.show_category_controls_button.name = 'Show categories'
            self.show_category_controls_button.button_style = 'outline'

    def _toggle_category_controls(self, *_):
        self.show_controls = not self.show_controls
        self.update_display()

    def _add_category(self, *_):
        category: str = self.category_input.value_input
        self.controller.add_category(category)

        self.category_input.value = ""
        self.category_input.value_input = ""
        self.controller.update_displays()

    def _remove_category(self, category: str):
        self.controller.remove_category(category)
        self.controller.update_displays()
