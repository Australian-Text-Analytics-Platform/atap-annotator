import logging
from typing import Optional, Union

import panel as pn
from atap_corpus.corpus.corpus import DataFrameCorpus
from atap_corpus_loader import CorpusLoader
from pandas import DataFrame, Series
from panel import Row, Column
from panel.layout import Divider
from panel.widgets import Select, Button, TextInput

from atap_annotator.annotator.CategoryControls import CategoryControls
from atap_annotator.annotator.Navigator import Navigator
from atap_annotator.annotator.DocumentDisplay import DocumentDisplay


class DefaultCategoryMarker:
    __slots__ = []

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        return ""


class Annotator(pn.viewable.Viewer):
    MIN_DOCUMENT_IDX: int = 1
    DOC_COL: str = DataFrameCorpus._COL_DOC
    DEFAULT_CATEGORIES_COL: str = 'annotation_category'

    def log(self, msg: str, level: int):
        logger = logging.getLogger(self.logger_name)
        logger.log(level, msg)

    def __init__(self, corpus_loader: CorpusLoader, logger_name: str, **params):
        super().__init__(**params)
        self.corpus_loader: CorpusLoader = corpus_loader
        self.logger_name: str = logger_name
        self.corpus_df: Optional[DataFrame] = None
        self.curr_document_idx: int = self.MIN_DOCUMENT_IDX
        self.default_categories: list[str] = []
        self.categories: list[str] = []

        self.corpus_selector = Select(name="Selected corpus", width=150)

        self.show_save_options: bool = False
        self.toggle_save_options_button = Button(name='Show save options',
                                                 button_type="success", button_style="outline")
        self.category_col_name_input = TextInput(name='New metadata name', value=self.DEFAULT_CATEGORIES_COL,
                                                 placeholder=self.DEFAULT_CATEGORIES_COL)
        self.corpus_name_input = TextInput(name='New corpus name')
        self.save_corpus_button = Button(name="Save as corpus",
                                         button_type="success", button_style="solid")
        self.save_corpus_controls = Column(
            self.toggle_save_options_button,
            Row(self.category_col_name_input, self.corpus_name_input, self.save_corpus_button)
        )

        self.category_controls = CategoryControls(self)
        self.document_display = DocumentDisplay(self)
        self.navigator = Navigator(self)

        self.panel = Row(
            self.document_display,
            Column(Row(self.corpus_selector,
                       self.save_corpus_controls,
                       self.category_controls),
                   Divider(),
                   Row(self.navigator)),
            sizing_mode='stretch_width'
        )

        self.corpus_selector.param.watch(self._update_selected_corpus, ['value'])
        self.toggle_save_options_button.on_click(self._toggle_save_options)
        self.save_corpus_button.on_click(self._save_as_corpus)
        self.corpus_loader.register_event_callback("update", self._update_corpus_list)

    def __panel__(self):
        return self.panel.servable()

    def display_error(self, error_msg: str):
        self.log(f"Error displayed: {error_msg}", logging.ERROR)
        pn.state.notifications.error(error_msg, duration=0)

    def display_warning(self, warning_msg: str):
        self.log(f"Warning displayed: {warning_msg}", logging.ERROR)
        pn.state.notifications.warning(warning_msg, duration=6000)

    def display_success(self, success_msg: str):
        self.log(f"Success displayed: {success_msg}", logging.INFO)
        pn.state.notifications.success(success_msg, duration=3000)

    def update_displays(self):
        self.category_controls.update_display()
        self.document_display.update_display()
        self.navigator.update_display()

    def _set_save_options(self):
        self.category_col_name_input.visible = self.show_save_options
        self.corpus_name_input.visible = self.show_save_options
        self.save_corpus_button.visible = self.show_save_options

        if self.show_save_options:
            self.toggle_save_options_button.name = 'Hide save options'
            self.toggle_save_options_button.button_style = 'solid'
        else:
            self.toggle_save_options_button.name = 'Show save options'
            self.toggle_save_options_button.button_style = 'outline'

    def _toggle_save_options(self, *_):
        self.show_save_options = not self.show_save_options
        self._set_save_options()

    def _reset_save_options(self):
        self.show_save_options = False
        self._set_save_options()
        self.category_col_name_input.value = ''
        self.corpus_name_input.value = ''

    def _update_corpus_list(self, *_):
        corpus_options: dict[str, DataFrameCorpus] = self.corpus_loader.get_corpora()
        self.corpus_selector.options = corpus_options
        if len(corpus_options) == 1:
            self.corpus_selector.value = list(corpus_options.values())[0]

    def _update_selected_corpus(self, *_):
        corpus: DataFrameCorpus = self.corpus_selector.value
        self.corpus_df = corpus.docs().to_frame().reset_index(drop=True)
        self.corpus_df[self.DEFAULT_CATEGORIES_COL] = DefaultCategoryMarker()
        self.corpus_df.index = range(1, len(self.corpus_df) + 1)
        self.curr_document_idx = self.MIN_DOCUMENT_IDX
        self._reset_save_options()
        self.update_displays()

    def _get_new_column_name(self, existing_columns: set[str]):
        iteration: int = 0
        new_col_name: str = self.DEFAULT_CATEGORIES_COL
        while new_col_name in existing_columns:
            new_col_name = f"{self.DEFAULT_CATEGORIES_COL}_{iteration}"
            iteration += 1

        return new_col_name

    def _resolve_categories(self, categories: Union[list[str], DefaultCategoryMarker],
                            default_categories_str: str) -> str:
        try:
            self.log(f"Resolved categories: {categories} into {','.join(categories)}", logging.DEBUG)
            return ','.join(categories)
        except TypeError:
            self.log(f"Resolved categories: {categories} into {default_categories_str}", logging.DEBUG)
            return default_categories_str

    def _save_as_corpus(self, *_):
        corpus: Optional[DataFrameCorpus] = self.corpus_selector.value
        corpus_df: Optional[DataFrame] = self.corpus_df
        if (corpus is None) or (corpus_df is None):
            self.display_warning("No corpus selected")
            return
        new_name: Optional[str] = self.corpus_name_input.value
        if len(new_name) == 0:
            new_name = None
        mask: Series[bool] = Series([True]*len(corpus_df))
        new_corpus: DataFrameCorpus = corpus.cloned(mask, name=new_name)

        category_col_name: str = self._get_new_column_name(set(corpus.metas))
        default_categories_str: str = ','.join(self.get_default_categories())
        category_col: Series[str] = corpus_df[self.DEFAULT_CATEGORIES_COL].apply(self._resolve_categories, args=(default_categories_str,))
        category_col = category_col.astype(str).reset_index(drop=True)
        self.log(f"New corpus created with annotation column: {category_col}", logging.DEBUG)
        new_corpus.add_meta(category_col, name=category_col_name)

        corpora = self.corpus_loader.get_mutable_corpora()
        corpora.add(new_corpus)
        self.corpus_loader.trigger_event("update")

        self._reset_save_options()
        self.display_success(f'Saved corpus as {new_name}')

    # DocumentDisplay methods

    def get_curr_document_text(self) -> str:
        document_text: str = ""
        if self.corpus_df is not None:
            document_text = self.corpus_df.at[self.curr_document_idx, self.DOC_COL]

        return document_text

    # CategoryControls methods

    def add_category(self, category: str):
        if category in self.categories:
            self.display_warning("This category has already been added")
            return
        self.categories.append(category)
        self.log(f"Category added: {category}", logging.DEBUG)

    def remove_category(self, category: str):
        if category in self.categories:
            self.categories.remove(category)
            self.log(f"Category removed: {category}", logging.DEBUG)

    # Navigator methods

    def get_curr_document_idx(self) -> int:
        return self.curr_document_idx

    def get_min_document_idx(self) -> int:
        if self.corpus_df is None:
            return self.MIN_DOCUMENT_IDX
        return self.corpus_df.index.min()

    def get_max_document_idx(self) -> int:
        if self.corpus_df is None:
            return self.MIN_DOCUMENT_IDX
        return self.corpus_df.index.max()

    def get_all_categories(self) -> list[str]:
        return self.categories.copy()

    def get_default_categories(self) -> list[str]:
        return self.default_categories.copy()

    def get_document_categories(self, document_idx: int) -> list[str]:
        if self.corpus_df is None:
            return []
        categories: Union[list[str], DefaultCategoryMarker] = self.corpus_df.at[document_idx, self.DEFAULT_CATEGORIES_COL]
        if isinstance(categories, DefaultCategoryMarker):
            return self.get_default_categories()
        else:
            return categories.copy()

    def get_curr_categories(self) -> list[str]:
        return self.get_document_categories(self.curr_document_idx)

    def set_curr_document_idx(self, new_document_idx: int):
        new_document_idx = min(new_document_idx, self.get_max_document_idx())
        new_document_idx = max(new_document_idx, self.get_min_document_idx())

        self.curr_document_idx = new_document_idx
        self.update_displays()
        self.log(f"Set curr_document_idx to {new_document_idx}", logging.DEBUG)

    def next_document(self):
        self.set_curr_document_idx(self.curr_document_idx + 1)

    def prev_document(self):
        self.set_curr_document_idx(self.curr_document_idx - 1)

    def set_curr_categories(self, categories: list[str]):
        if self.corpus_df is None:
            return
        self.corpus_df.at[self.curr_document_idx, self.DEFAULT_CATEGORIES_COL] = categories.copy()

        self.log(f"Set categories for document {self.curr_document_idx} to {categories}", logging.DEBUG)

    def set_default_categories(self, categories: list[str]):
        self.default_categories = categories.copy()
        self.log(f"Set default categories to {categories}", logging.DEBUG)
