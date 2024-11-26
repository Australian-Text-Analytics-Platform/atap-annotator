from panel import Column
from panel.pane import Markdown


class DocumentDisplay:
    """
    Controls the document view and rendering
    """
    def __init__(self, controller):
        self.controller = controller

        self.document_display = Markdown()
        self.panel = Column(self.document_display, sizing_mode="stretch_width")

    def __panel__(self):
        return self.panel

    def update_display(self):
        document_text: str = self.controller.get_curr_document_text()
        self.document_display.object = document_text
