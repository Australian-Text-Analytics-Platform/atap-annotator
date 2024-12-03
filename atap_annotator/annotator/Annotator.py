import logging
import traceback
from typing import Optional

import pandas as pd
import panel as pn
from atap_corpus.corpus.corpus import DataFrameCorpus
from atap_corpus_loader import CorpusLoader
from pandas import DataFrame, Series
from panel import Row, Column
from panel.layout import Divider

from atap_annotator.annotator.SettingsControls import SettingsControls
from atap_annotator.annotator.Navigator import Navigator
from atap_annotator.annotator.MetaDisplay import MetaDisplay


class DefaultCategoryMarker:
    __slots__ = []

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        return ""


class Annotator(pn.viewable.Viewer):
    MIN_DOCUMENT_IDX: int = 1
    DOC_COL: str = DataFrameCorpus._COL_DOC
    DEFAULT_CATEGORIES_COL: str = 'annotation'

    def log(self, msg: str, level: int):
        logger = logging.getLogger(self.logger_name)
        logger.log(level, msg)

    def __init__(self, corpus_loader: CorpusLoader, logger_name: str, **params):
        super().__init__(**params)
        self.corpus_loader: CorpusLoader = corpus_loader
        self.logger_name: str = logger_name
        self.corpus: Optional[DataFrameCorpus] = None
        self.corpus_df: Optional[DataFrame] = None
        self.annotations: Optional[Series] = None
        self.curr_document_idx: int = self.MIN_DOCUMENT_IDX
        self.categories: list[str] = []
        self.default_category: Optional[str] = None

        self.meta_display = MetaDisplay(self)
        self.navigator = Navigator(self)
        self.settings_controls = SettingsControls(self)

        self.panel = Row(
            self.meta_display,
            Column(self.navigator,
                   Divider(),
                   self.settings_controls),
            sizing_mode='stretch_width'
        )

        self.corpus_loader.register_event_callback("update", self.update_displays)

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
        self.settings_controls.update_display()
        self.meta_display.update_display()
        self.navigator.update_display()

    def get_corpus_dict(self) -> dict[str, DataFrameCorpus]:
        return self.corpus_loader.get_corpora()

    def set_selected_corpus(self, corpus: Optional[DataFrameCorpus]):
        if corpus == self.corpus:
            # Prevents endless recursive loop through update_displays()
            return
        elif corpus is None:
            self.corpus = None
            self.corpus_df = None
            self.annotations = None
        else:
            self.corpus = corpus
            self.corpus_df = corpus.to_dataframe().reset_index(drop=True)
            self.corpus_df.index = range(1, len(self.corpus) + 1)
            self.annotations = Series(len(self.corpus) * [DefaultCategoryMarker()])
            self.annotations.index = range(1, len(self.corpus) + 1)
            self.default_category = None
        self.curr_document_idx = self.MIN_DOCUMENT_IDX
        self.update_displays()

    def _get_new_column_name(self, provided_name: str, existing_columns: set[str]) -> str:
        iteration: int = 0
        if len(provided_name) == 0:
            provided_name = self.DEFAULT_CATEGORIES_COL
        while provided_name in existing_columns:
            provided_name = f"{provided_name}_{iteration}"
            iteration += 1

        return provided_name

    def _resolve_annotations_col(self, annotations_col: Series) -> Series:
        # Converts an annotations Series to a column to be included in a corpus
        def resolver(x):
            return str(x) if x else None
        return annotations_col.apply(resolver).reset_index(drop=True)

    def _unresolve_annotations_col(self, annotations_col: Series) -> Series:
        # Converts a column from the corpus to an annotations Series
        def unresolver(x):
            if (x is None) or (pd.isna(x)):
                return None
            elif len(x) == 0:
                return DefaultCategoryMarker()
            return str(x)
        annotations_col = annotations_col.apply(unresolver)
        annotations_col.index = range(1, len(annotations_col) + 1)

        return annotations_col

    def save_as_corpus(self, new_name: str, selected_meta: str, overwrite_meta: bool):
        if self.corpus is None:
            self.display_warning("No corpus selected")
            return
        if len(new_name) == 0:
            new_name = None
        mask: Series = Series([True]*len(self.corpus))
        cloned_corpus: DataFrameCorpus = self.corpus.cloned(mask, new_name)
        new_name = cloned_corpus.name
        new_corpus: DataFrameCorpus = cloned_corpus.detached()
        del cloned_corpus
        new_corpus.rename(new_name)
        annotations_col: Series = self._resolve_annotations_col(self.annotations)
        if overwrite_meta:
            orig_col: Series = new_corpus[selected_meta]
            annotations_col.fillna(orig_col)
            new_corpus.remove_meta(selected_meta)
        annotations_col = annotations_col.astype('category')
        annotations_col_name: str = self._get_new_column_name(selected_meta, set(self.corpus.metas))
        new_corpus.add_meta(annotations_col, name=annotations_col_name)

        corpora = self.corpus_loader.get_mutable_corpora()
        corpora.add(new_corpus)
        self.corpus_loader.trigger_event("update")

        self.display_success(f'Saved corpus as {new_name}')

    # MetaDisplay methods

    def get_all_metas(self) -> list[str]:
        if self.corpus is None:
            return []
        return [self.corpus._COL_DOC] + self.corpus.metas

    def get_curr_meta_str(self, meta: str) -> str:
        if (self.corpus is None) or (meta not in self.get_all_metas()):
            return ""
        return str(self.corpus_df.at[self.curr_document_idx, meta])

    # SettingsControls methods

    def add_category(self, category: str):
        if category in self.categories:
            self.display_warning("This category has already been added")
            return
        if len(category) == 0:
            self.display_warning("Category cannot be empty")
            return
        self.categories.append(category)
        self.log(f"Category added: {category}", logging.DEBUG)

    def remove_category(self, category: str):
        if category in self.categories:
            self.categories.remove(category)
            self.log(f"Category removed: {category}", logging.DEBUG)

    def get_categorical_metas(self) -> list[str]:
        if self.corpus is None:
            return []
        return self.corpus_df.select_dtypes(include='category').columns.tolist()

    def set_annotated_meta_col(self, meta: str):
        try:
            if (self.corpus_df is None) or (meta not in self.corpus_df.columns):
                return
            metas: list[str] = self.corpus_df.select_dtypes(include='category').columns.tolist()
            if meta not in metas:
                return
            self.annotations = self._unresolve_annotations_col(self.corpus_df[meta])
            self.categories = [x for x in self.annotations.unique() if isinstance(x, str)]
            self.log(','.join([f"{c}:{type(c)}" for c in self.categories]), logging.DEBUG)
            self.update_displays()
        except Exception as e:
            self.log(traceback.format_exc(), logging.DEBUG)

    # Navigator methods

    def get_curr_document_idx(self) -> int:
        return self.curr_document_idx

    def get_min_document_idx(self) -> int:
        if self.annotations is None:
            return self.MIN_DOCUMENT_IDX
        return self.annotations.index.min()

    def get_max_document_idx(self) -> int:
        if self.annotations is None:
            return self.MIN_DOCUMENT_IDX
        return self.annotations.index.max()

    def get_all_categories(self) -> list[str]:
        return self.categories.copy()

    def get_default_category(self) -> Optional[str]:
        return self.default_category

    def get_document_category(self, document_idx: int) -> Optional[str]:
        if self.annotations is None:
            return ''
        category = self.annotations.at[document_idx]
        if isinstance(category, DefaultCategoryMarker):
            return self.get_default_category()
        else:
            return category

    def get_curr_category(self) -> Optional[str]:
        return self.get_document_category(self.curr_document_idx)

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

    def set_curr_category(self, category: str):
        if self.annotations is None:
            return
        self.annotations.at[self.curr_document_idx] = category
        self.log(f"Set category for document {self.curr_document_idx} to {category}", logging.DEBUG)

    def set_default_category(self, category: str):
        self.default_category = category
        self.log(f"Set default category to {category}", logging.DEBUG)
