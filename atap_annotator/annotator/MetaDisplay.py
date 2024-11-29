from panel import Column, Tabs


class MetaDisplay:
    """
    Controls the document view and rendering
    """
    TAB_WIDTH: int = 900
    COL_HEIGHT: int = 500

    def __init__(self, controller):
        self.controller = controller

        self.panel = Tabs(tabs_location='left', width=self.TAB_WIDTH)

    def __panel__(self):
        return self.panel

    def update_display(self):
        col_objs: list[Column] = []
        for meta_name in self.controller.get_all_metas():
            meta_text: str = self.controller.get_curr_meta_str(meta_name)
            col_objs.append(Column(meta_text, height=self.COL_HEIGHT, name=meta_name, scroll=True))
        self.panel.objects = col_objs
