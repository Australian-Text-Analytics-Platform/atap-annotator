from atap_corpus.corpus.corpus import DataFrameCorpus
from panel import Row, Column, FlexBox
from panel.widgets import Button, TextInput, Select, Checkbox


class SettingsControls:
    STANDARD_WIDTH: int = 150

    def __init__(self, controller):
        self.controller = controller
        self.show_controls: bool = False

        # Corpus controls
        self.corpus_selector = Select(name='Selected corpus', width=self.STANDARD_WIDTH)
        self.corpus_name_input = TextInput(name='New corpus name', width=self.STANDARD_WIDTH)
        self.save_corpus_button = Button(name='Save as corpus', button_type='success', button_style='solid')
        corpus_controls = Column(self.corpus_selector,
                                 self.corpus_name_input,
                                 self.save_corpus_button)

        # Column controls
        self.new_meta_col: str = '<New metadata>'
        self.meta_col_select = Select(name='Annotated metadata', width=self.STANDARD_WIDTH, options=[self.new_meta_col])
        self.meta_col_name_input = TextInput(name='Annotated metadata', width=self.STANDARD_WIDTH,
                                             placeholder=self.controller.DEFAULT_CATEGORIES_COL)
        self.overwrite_meta_checkbox = Checkbox(name='Overwrite', disabled=True, value=False)
        column_controls = Column(self.meta_col_select,
                                 self.meta_col_name_input,
                                 self.overwrite_meta_checkbox)

        # Category controls
        self.category_input = TextInput(name='Category', width=self.STANDARD_WIDTH)
        self.add_category_button = Button(
            name="Add category",
            button_type="success", button_style="solid",
            align='end', width=120
        )
        self.remove_category_buttons = FlexBox()
        category_inputs = Column(self.category_input,
                                 self.add_category_button,
                                 self.remove_category_buttons,
                                 width=self.STANDARD_WIDTH)

        self.panel = Row(corpus_controls, column_controls, category_inputs)

        self.add_category_button.on_click(self._add_category)
        self.save_corpus_button.on_click(self._save_corpus)
        self.corpus_selector.param.watch(self._update_selected_corpus, ['value'])
        self.meta_col_select.param.watch(self._update_selected_meta_col, ['value'])
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
        self._update_corpus_list()

    def _update_corpus_list(self):
        corpus_options: dict[str, DataFrameCorpus] = self.controller.get_corpus_dict()
        self.corpus_selector.options = corpus_options
        if len(corpus_options) == 1:
            self.corpus_selector.value = list(self.corpus_selector.options.values())[0]

    def _update_selected_corpus(self, *_):
        self.controller.set_selected_corpus(self.corpus_selector.value)
        meta_cols: list[str] = [self.new_meta_col] + self.controller.get_categorical_metas()
        self.meta_col_select.options = meta_cols

    def _update_selected_meta_col(self, *_):
        selected_col: str = self.meta_col_select.value
        no_col_selected: bool = selected_col == self.new_meta_col
        self.meta_col_name_input.visible = no_col_selected
        self.overwrite_meta_checkbox.disabled = no_col_selected
        if no_col_selected:
            self.overwrite_meta_checkbox.value = False
        else:
            self.controller.set_annotated_meta_col(selected_col)

    def _add_category(self, *_):
        category: str = self.category_input.value_input
        self.controller.add_category(category)

        self.category_input.value = ""
        self.category_input.value_input = ""
        self.controller.update_displays()

    def _remove_category(self, category: str):
        self.controller.remove_category(category)
        self.controller.update_displays()

    def _save_corpus(self, *_):
        corpus_name: str = self.corpus_name_input.value
        keep_original_meta: str = self.overwrite_meta_checkbox.value
        selected_col: str = self.meta_col_select.value
        if selected_col == self.new_meta_col:
            selected_col = self.meta_col_name_input.value

        self.controller.save_as_corpus(corpus_name, selected_col, keep_original_meta)
